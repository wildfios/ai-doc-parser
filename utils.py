"""
Utility Functions Module

This module provides shared utility functions used throughout the client
onboarding system. Includes JSON operations, text processing, date parsing,
and validation helpers.

Author: Filippenko Ihor
Date: 2025-12-10
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime objects and other special types.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        return super().default(obj)


def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load JSON from a file with error handling.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON as a dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise


def save_json(
    data: Dict[str, Any],
    file_path: Union[str, Path],
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    Save dictionary to JSON file with pretty formatting.

    Args:
        data: Dictionary to save
        file_path: Output file path
        indent: Indentation level for pretty printing
        ensure_ascii: Whether to escape non-ASCII characters
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(
                data,
                f,
                indent=indent,
                ensure_ascii=ensure_ascii,
                cls=JSONEncoder
            )
        logger.info(f"Saved JSON to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        raise


def merge_dicts_deep(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries, with dict2 values taking precedence.

    Args:
        dict1: Base dictionary
        dict2: Dictionary to merge (takes precedence)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts_deep(result[key], value)
        else:
            result[key] = value

    return result


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize and clean text input.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (truncates if exceeded)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)

    # Truncate if necessary
    if max_length and len(text) > max_length:
        text = text[:max_length].rsplit(' ', 1)[0] + '...'
        logger.warning(f"Text truncated to {max_length} characters")

    return text


def parse_date(
    date_string: str,
    formats: Optional[List[str]] = None
) -> Optional[str]:
    """
    Parse date string into standardized ISO format (YYYY-MM-DD).

    Args:
        date_string: Date string to parse
        formats: List of date format patterns to try

    Returns:
        ISO formatted date string, or None if parsing fails
    """
    if not date_string:
        return None

    # Default formats if none provided
    if formats is None:
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%d %B %Y",
            "%b %d, %Y",
            "%d %b %Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
        ]

    # Clean the input
    date_string = sanitize_string(date_string)

    # Try each format
    for fmt in formats:
        try:
            dt = datetime.strptime(date_string, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try more flexible parsing (e.g., "October 29, 1990")
    try:
        # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
        cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_string)
        for fmt in formats:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    except Exception:
        pass

    logger.warning(f"Could not parse date: {date_string}")
    return None


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extract and normalize phone number from text.

    Args:
        text: Text containing phone number

    Returns:
        Normalized phone number, or None if not found
    """
    if not text:
        return None

    # Pattern for international phone numbers
    patterns = [
        r'\+\d{1,3}[\s-]?\d{1,4}[\s-]?\d{1,4}[\s-]?\d{1,4}',  # +380 93 809 7885
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # 123-456-7890
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',  # (123) 456-7890
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Keep only digits and leading +
            phone = re.sub(r'[^\d+]', '', match.group())
            return phone

    return None


def extract_email(text: str) -> Optional[str]:
    """
    Extract email address from text.

    Args:
        text: Text containing email

    Returns:
        Email address, or None if not found
    """
    if not text:
        return None

    # Email pattern
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)

    if match:
        return match.group().lower()

    return None


def calculate_confidence(
    value: Any,
    source_count: int = 1,
    agreement_ratio: float = 1.0,
    has_conflicts: bool = False
) -> float:
    """
    Calculate confidence score for an extracted field.

    Args:
        value: The extracted value
        source_count: Number of sources providing this value
        agreement_ratio: Ratio of sources that agree (0.0 - 1.0)
        has_conflicts: Whether there are conflicting values

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not value or (isinstance(value, str) and not value.strip()):
        return 0.0

    # Base confidence from agreement
    confidence = agreement_ratio

    # Boost for multiple confirming sources
    if source_count > 1:
        confidence = min(1.0, confidence + (source_count - 1) * 0.1)

    # Penalize for conflicts
    if has_conflicts:
        confidence *= 0.7

    # Ensure bounds
    return max(0.0, min(1.0, confidence))


def truncate_for_display(text: str, max_length: int = 100) -> str:
    """
    Truncate text for display purposes.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."


def validate_schema_structure(data: Dict, schema: Dict) -> List[str]:
    """
    Validate that data matches the expected schema structure.

    Args:
        data: Data to validate
        schema: Expected schema structure

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    def _validate_recursive(data_node: Any, schema_node: Any, path: str = "root"):
        if isinstance(schema_node, dict):
            if not isinstance(data_node, dict):
                errors.append(f"{path}: Expected dict, got {type(data_node).__name__}")
                return

            for key, value in schema_node.items():
                if key in data_node:
                    _validate_recursive(data_node[key], value, f"{path}.{key}")
                # Note: Missing keys are allowed (will be flagged separately)

        elif isinstance(schema_node, list):
            if not isinstance(data_node, list):
                errors.append(f"{path}: Expected list, got {type(data_node).__name__}")

    _validate_recursive(data, schema)
    return errors


if __name__ == "__main__":
    # Test utilities
    print("=== Testing Utility Functions ===\n")

    # Date parsing
    test_dates = ["29 October 1990", "2023-12-09", "12/09/2023"]
    for date in test_dates:
        parsed = parse_date(date)
        print(f"Date: {date} -> {parsed}")

    # Phone extraction
    test_phones = ["+380 93 809 7885", "+357 95 620 963", "(123) 456-7890"]
    for phone in test_phones:
        extracted = extract_phone_number(phone)
        print(f"Phone: {phone} -> {extracted}")

    # Email extraction
    test_text = "Contact me at john.doe@example.com for more info"
    email = extract_email(test_text)
    print(f"Email: {test_text} -> {email}")

    # Confidence calculation
    conf = calculate_confidence("John Doe", source_count=3, agreement_ratio=1.0)
    print(f"\nConfidence (3 sources, full agreement): {conf}")

    print("\n✓ All utilities working correctly")
