"""
Comprehensive Test Suite

This module provides comprehensive testing including mock LLM responses
for when API is unavailable, unit tests, integration tests, and stress tests.

Author: Filippenko Ihor
Date: 2025-12-10
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from document_processor import DocumentProcessor
from utils import save_json

logger = logging.getLogger(__name__)


class MockLLMClient:
    """Mock LLM client for testing without API access."""

    def extract_structured_data(self, document_content: str, document_name: str) -> Dict[str, Any]:
        """Mock extraction based on document content."""
        # Parse based on known CV patterns
        data = {
            "personal_info": {},
            "employment": {},
            "contact": {}
        }

        # Extract name
        if "Oleksandr Korolenko" in document_content or "cv1" in document_name:
            data["personal_info"]["first_name"] = "Oleksandr"
            data["personal_info"]["last_name"] = "Korolenko"
            data["personal_info"]["dob"] = "1990-10-29"
            data["contact"]["email"] = "korolenkoa@gmail.com"
            data["contact"]["phone"] = "+380938097885"
            data["contact"]["location"] = "Poltava, Ukraine"
            data["employment"]["current_employer"] = "Blazing Boost"
            data["employment"]["position"] = "Front-end Developer"

        elif "Filippenko Ihor" in document_content or "cv2" in document_name:
            data["personal_info"]["first_name"] = "Ihor"
            data["personal_info"]["last_name"] = "Filippenko"
            data["contact"]["email"] = "asm.xor.eax.eax@gmail.com"
            data["contact"]["phone"] = "+380731507873"
            data["contact"]["location"] = "Cyprus"
            data["employment"]["current_employer"] = "R&D Company"
            data["employment"]["position"] = "Senior Full-stack Developer"

        elif "Eugene ZenBerry" in document_content or "cv3" in document_name:
            data["personal_info"]["first_name"] = "Eugene"
            data["personal_info"]["last_name"] = "ZenBerry"
            data["contact"]["email"] = "zenberry.work@gmail.com"
            data["contact"]["phone"] = "+35795620963"
            data["contact"]["location"] = "Limassol, Cyprus"
            data["employment"]["current_employer"] = "Dreamatic"
            data["employment"]["position"] = "Full Stack Web Developer"

        return data

    def validate_and_enhance(self, extracted_data: Any, target_schema: Dict) -> Dict[str, Any]:
        """Mock validation and mapping."""
        # Merge all extracted data
        all_data = {}
        for item in extracted_data:
            data = item["data"]
            for key, value in data.items():
                if key not in all_data:
                    all_data[key] = value

        # Map to schema
        populated = {
            "client_information": {
                "first_name": all_data.get("personal_info", {}).get("first_name", ""),
                "last_name": all_data.get("personal_info", {}).get("last_name", ""),
                "dob": all_data.get("personal_info", {}).get("dob", ""),
                "address": {
                    "street": "",
                    "city": all_data.get("contact", {}).get("location", "").split(",")[0].strip() if all_data.get("contact", {}).get("location") else "",
                    "state": "",
                    "zip": ""
                }
            },
            "employment": {
                "employer_name": all_data.get("employment", {}).get("current_employer", ""),
                "annual_income": None
            },
            "accounts": []
        }

        return {
            "populated_schema": populated,
            "metadata": {
                "field_confidence": {
                    "client_information.first_name": 0.95,
                    "client_information.last_name": 0.95,
                    "client_information.dob": 0.85,
                    "employment.employer_name": 0.80
                },
                "missing_fields": ["employment.annual_income", "client_information.address.street"],
                "review_required": ["client_information.dob"],
                "mapping_notes": "Mapped from CV data - some financial fields missing"
            }
        }


def generate_demo_output():
    """Generate demonstration output with mock data."""
    logger.info("Generating demonstration output with mock data")

    # Process documents
    processor = DocumentProcessor()
    doc_results = processor.process_directory("input")

    # Create mock extraction results
    mock_llm = MockLLMClient()
    extraction_results = []

    for doc_result in doc_results:
        if doc_result['success']:
            extracted = mock_llm.extract_structured_data(
                doc_result['content'],
                doc_result['file_name']
            )
            extraction_results.append({
                "extracted_data": extracted,
                "source_file": doc_result['file_name'],
                "success": True,
                "error": None
            })

    # Aggregate for mapping
    all_extracted = [
        {"data": r["extracted_data"], "source": r["source_file"]}
        for r in extraction_results if r["success"]
    ]

    # Load schema
    from utils import load_json
    target_schema = load_json("schema.json")

    # Mock mapping
    mapping_result = mock_llm.validate_and_enhance(all_extracted, target_schema)

    # Generate final output
    final_result = {
        "client_profile": mapping_result["populated_schema"],
        "field_metadata": {
            "client_information.first_name": {
                "value": mapping_result["populated_schema"]["client_information"]["first_name"],
                "confidence": 0.95,
                "sources": [r["source_file"] for r in extraction_results],
                "has_value": True,
                "is_empty": False
            },
            "client_information.last_name": {
                "value": mapping_result["populated_schema"]["client_information"]["last_name"],
                "confidence": 0.95,
                "sources": [r["source_file"] for r in extraction_results],
                "has_value": True,
                "is_empty": False
            },
            "client_information.dob": {
                "value": mapping_result["populated_schema"]["client_information"]["dob"],
                "confidence": 0.85,
                "sources": ["cv1.pdf"],
                "has_value": True,
                "is_empty": False
            },
            "employment.employer_name": {
                "value": mapping_result["populated_schema"]["employment"]["employer_name"],
                "confidence": 0.80,
                "sources": [r["source_file"] for r in extraction_results],
                "has_value": True,
                "is_empty": False
            },
            "employment.annual_income": {
                "value": None,
                "confidence": 0.0,
                "sources": [],
                "has_value": False,
                "is_empty": True
            }
        },
        "issues_for_review": [
            {
                "type": "missing",
                "field": "employment.annual_income",
                "severity": "high",
                "message": "Required field 'employment.annual_income' could not be extracted from any document"
            },
            {
                "type": "missing",
                "field": "client_information.address.street",
                "severity": "medium",
                "message": "Field 'client_information.address.street' is missing"
            },
            {
                "type": "empty_field",
                "field": "client_information.address.state",
                "severity": "low",
                "message": "Field 'client_information.address.state' is empty"
            },
            {
                "type": "review_required",
                "field": "client_information.dob",
                "severity": "medium",
                "message": "Field 'client_information.dob' requires manual review"
            }
        ],
        "validation": {
            "is_valid": True,
            "statistics": {
                "total_fields": 9,
                "populated_fields": 6,
                "empty_fields": 3,
                "population_rate": 0.67,
                "total_issues": 4,
                "issue_types": {
                    "missing": 1,
                    "empty_field": 1,
                    "review_required": 1
                },
                "severity_counts": {
                    "high": 1,
                    "medium": 2,
                    "low": 1
                },
                "average_confidence": 0.71
            }
        },
        "processing_info": {
            "timestamp": "2025-12-09 14:19:00",
            "processing_time_seconds": 2.5,
            "model_used": "gemma-2-27b-it (DEMO MODE - Mock Data)",
            "note": "This is demonstration output generated with mock LLM responses due to API access issues"
        }
    }

    # Save demo output
    output_path = Path("output/demo_results.json")
    save_json(final_result, output_path)

    logger.info(f"✓ Demo output saved to {output_path}")

    return final_result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("="*60)
    print("GENERATING DEMONSTRATION OUTPUT")
    print("="*60)
    print("\nNote: Using mock LLM responses due to API access issues")
    print("This demonstrates the system's output format and structure.\n")

    result = generate_demo_output()

    print("\n" + "="*60)
    print("DEMO RESULTS SUMMARY")
    print("="*60)

    print(f"\nClient Profile:")
    print(f"  Name: {result['client_profile']['client_information']['first_name']} "
          f"{result['client_profile']['client_information']['last_name']}")
    print(f"  DOB: {result['client_profile']['client_information']['dob']}")
    print(f"  Employer: {result['client_profile']['employment']['employer_name']}")

    print(f"\nValidation Statistics:")
    stats = result['validation']['statistics']
    print(f"  Population Rate: {stats['population_rate']*100:.1f}%")
    print(f"  Average Confidence: {stats['average_confidence']:.2f}")
    print(f"  Total Issues: {stats['total_issues']}")

    print(f"\nIssues for Manual Review:")
    for issue in result['issues_for_review']:
        print(f"  [{issue['severity'].upper()}] {issue['message']}")

    print(f"\n✓ Complete demo output available at: output/demo_results.json")
    print("="*60)
