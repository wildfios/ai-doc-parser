"""
Validator Module

This module validates populated schemas, enforces data quality rules,
and generates comprehensive issue reports for manual review.

Author: Filippenko Ihor
Date: 2025-12-10
"""

import logging
from typing import Any, Dict, List
import re

from config import get_config
from utils import validate_schema_structure

logger = logging.getLogger(__name__)


class Validator:
    """
    Validates populated schemas and generates issue reports.

    Performs:
    - Schema structure validation
    - Data type and format validation
    - Completeness checks
    - Confidence threshold enforcement
    """

    def __init__(self):
        """Initialize validator with configuration."""
        self.config = get_config()

    def validate(
        self,
        populated_schema: Dict[str, Any],
        target_schema: Dict[str, Any],
        metadata: Dict[str, Dict[str, Any]],
        existing_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate populated schema and generate comprehensive report.

        Args:
            populated_schema: Schema populated with extracted data
            target_schema: Original target schema structure
            metadata: Field-level metadata
            existing_issues: Issues detected during mapping

        Returns:
            Dictionary containing:
                - is_valid: Overall validation status
                - validation_errors: List of validation errors
                - all_issues: Combined list of all issues
                - statistics: Validation statistics
        """
        logger.info("Validating populated schema")

        validation_errors = []
        additional_issues = []

        # 1. Schema structure validation
        structure_errors = validate_schema_structure(populated_schema, target_schema)
        validation_errors.extend([
            {"type": "structure_error", "message": err}
            for err in structure_errors
        ])

        # 2. Data type validation
        type_errors = self._validate_types(populated_schema)
        validation_errors.extend(type_errors)

        # 3. Format validation
        format_errors = self._validate_formats(populated_schema)
        validation_errors.extend(format_errors)

        # 4. Confidence validation
        confidence_issues = self._validate_confidence(metadata)
        additional_issues.extend(confidence_issues)

        # 5. Completeness check
        completeness_issues = self._check_completeness(populated_schema, target_schema)
        additional_issues.extend(completeness_issues)

        # Combine all issues
        all_issues = existing_issues + validation_errors + additional_issues

        # Calculate statistics
        stats = self._calculate_statistics(
            populated_schema,
            metadata,
            all_issues
        )

        is_valid = len(validation_errors) == 0

        logger.info(
            f"Validation complete: "
            f"{'PASSED' if is_valid else 'FAILED'} "
            f"({len(all_issues)} total issues)"
        )

        return {
            "is_valid": is_valid,
            "validation_errors": validation_errors,
            "all_issues": all_issues,
            "statistics": stats
        }

    def _validate_types(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate data types in schema.

        Args:
            schema: Populated schema

        Returns:
            List of type validation errors
        """
        errors = []

        # Validate employment_data.client_1.annual_income is numeric or null
        if 'employment_data' in schema and 'client_1' in schema['employment_data']:
            income = schema['employment_data']['client_1'].get('annual_income')
            if income is not None and not isinstance(income, (int, float)):
                errors.append({
                    "type": "type_error",
                    "field": "employment_data.client_1.annual_income",
                    "message": f"annual_income must be numeric, got {type(income).__name__}",
                    "severity": "high"
                })

        # Validate non_retirement_assets is a list
        if 'non_retirement_assets' in schema:
            if not isinstance(schema['non_retirement_assets'], list):
                errors.append({
                    "type": "type_error",
                    "field": "non_retirement_assets",
                    "message": f"non_retirement_assets must be a list, got {type(schema['non_retirement_assets']).__name__}",
                    "severity": "high"
                })

        return errors

    def _validate_formats(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate data formats in schema.

        Args:
            schema: Populated schema

        Returns:
            List of format validation errors
        """
        errors = []

        # Validate DOB format (should be YYYY-MM-DD)
        if 'general_information' in schema and 'client_1' in schema['general_information']:
            dob = schema['general_information']['client_1'].get('dob')
            if dob and not self._is_valid_date_format(dob):
                errors.append({
                    "type": "format_error",
                    "field": "general_information.client_1.dob",
                    "message": f"Invalid date format: {dob} (expected YYYY-MM-DD)",
                    "severity": "medium"
                })

        # Validate ZIP code (if present)
        if 'general_information' in schema:
            address = schema['general_information'].get('home_address', {})
            if isinstance(address, dict) and 'zip' in address:
                zip_code = address['zip']
                if zip_code and not self._is_valid_zip(zip_code):
                    errors.append({
                        "type": "format_error",
                        "field": "general_information.home_address.zip",
                        "message": f"Invalid ZIP code format: {zip_code}",
                        "severity": "low"
                    })

        return errors

    def _validate_confidence(
        self,
        metadata: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate confidence scores and flag low-confidence fields.

        Args:
            metadata: Field-level metadata

        Returns:
            List of confidence-related issues
        """
        issues = []

        threshold = self.config.validation.require_manual_review_threshold

        for field_path, meta in metadata.items():
            confidence = meta.get('confidence', 0.0)

            if confidence < threshold and meta.get('has_value'):
                issues.append({
                    "type": "low_confidence",
                    "field": field_path,
                    "message": f"Confidence {confidence:.2f} below threshold {threshold}",
                    "severity": "medium",
                    "confidence": confidence
                })

        return issues

    def _check_completeness(
        self,
        populated_schema: Dict[str, Any],
        target_schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Check for missing or empty fields.

        Args:
            populated_schema: Populated schema
            target_schema: Target schema

        Returns:
            List of completeness issues
        """
        issues = []

        def check_node(pop_node: Any, target_node: Any, path: str = ""):
            if isinstance(target_node, dict):
                for key, target_value in target_node.items():
                    field_path = f"{path}.{key}" if path else key

                    if key not in pop_node:
                        issues.append({
                            "type": "missing_field",
                            "field": field_path,
                            "message": f"Field '{field_path}' is missing",
                            "severity": "medium"
                        })
                    elif not isinstance(target_value, (dict, list)):
                        # Check if empty
                        value = pop_node[key]
                        if not value and value != 0:  # 0 is valid
                            issues.append({
                                "type": "empty_field",
                                "field": field_path,
                                "message": f"Field '{field_path}' is empty",
                                "severity": "low"
                            })
                    else:
                        # Recurse
                        if key in pop_node:
                            check_node(pop_node[key], target_value, field_path)

        check_node(populated_schema, target_schema)

        return issues

    def _calculate_statistics(
        self,
        populated_schema: Dict[str, Any],
        metadata: Dict[str, Dict[str, Any]],
        all_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate validation statistics.

        Args:
            populated_schema: Populated schema
            metadata: Field-level metadata
            all_issues: All detected issues

        Returns:
            Statistics dictionary
        """
        total_fields = len(metadata)
        populated_fields = sum(1 for m in metadata.values() if m.get('has_value'))
        empty_fields = total_fields - populated_fields

        # Issue breakdown
        issue_types = {}
        severity_counts = {"high": 0, "medium": 0, "low": 0}

        for issue in all_issues:
            issue_type = issue.get('type', 'unknown')
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

            severity = issue.get('severity', 'medium')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Average confidence
        confidences = [m.get('confidence', 0.0) for m in metadata.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_fields": total_fields,
            "populated_fields": populated_fields,
            "empty_fields": empty_fields,
            "population_rate": populated_fields / total_fields if total_fields > 0 else 0.0,
            "total_issues": len(all_issues),
            "issue_types": issue_types,
            "severity_counts": severity_counts,
            "average_confidence": avg_confidence
        }

    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string matches YYYY-MM-DD format."""
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        return bool(re.match(pattern, date_str))

    def _is_valid_zip(self, zip_code: str) -> bool:
        """Check if ZIP code format is valid (US format)."""
        # US ZIP: 12345 or 12345-6789
        pattern = r'^\d{5}(-\d{4})?$'
        return bool(re.match(pattern, str(zip_code)))


if __name__ == "__main__":
    # Test validator
    logging.basicConfig(level=logging.INFO)

    print("=== Testing Validator ===\n")

    from utils import load_json

    try:
        # Create test data
        target_schema = load_json("schema.json")

        populated_schema = {
            "client_information": {
                "first_name": "John",
                "last_name": "Doe",
                "dob": "1990-10-29",
                "address": {
                    "street": "123 Main St",
                    "city": "Kyiv",
                    "state": "Kyiv",
                    "zip": "12345"
                }
            },
            "employment": {
                "employer_name": "Test Corp",
                "annual_income": 50000
            },
            "accounts": []
        }

        metadata = {
            "client_information.first_name": {"confidence": 0.9, "has_value": True},
            "client_information.last_name": {"confidence": 0.9, "has_value": True},
            "client_information.dob": {"confidence": 0.8, "has_value": True},
            "employment.employer_name": {"confidence": 0.7, "has_value": True},
            "employment.annual_income": {"confidence": 0.4, "has_value": True},
        }

        validator = Validator()
        result = validator.validate(
            populated_schema,
            target_schema,
            metadata,
            existing_issues=[]
        )

        print(f"Validation: {'PASSED' if result['is_valid'] else 'FAILED'}")
        print(f"Statistics:")
        for key, value in result['statistics'].items():
            print(f"  - {key}: {value}")

        print(f"\n✓ Validator test complete")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise
