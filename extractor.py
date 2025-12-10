"""
Information Extractor Module

This module orchestrates the extraction of structured information from
document content using the OpenAI Files/Responses API.

Author: Filippenko Ihor
Date: 2025-12-10
"""

import logging
import json
import sys
from typing import Dict, List, Any, Optional
from openai import OpenAI

from config import get_config

logger = logging.getLogger(__name__)


class Extractor:
    """
    Extracts structured information from document files using OpenAI Responses API.
    """

    def __init__(self, target_schema: Dict[str, Any]):
        """
        Initialize extractor with configuration and target schema.

        Args:
            target_schema: The schema to populate
        """
        self.config = get_config()
        self.client = OpenAI(api_key=self.config.api.api_key)
        self.target_schema = target_schema

    def extract_from_files(self, file_ids: List[str]) -> Dict[str, Any]:
        """
        Extract structured information from multiple files using OpenAI Responses API.

        Args:
            file_ids: List of OpenAI File IDs to process

        Returns:
            Dictionary containing populated schema and issues info.
        """
        logger.info(f"Extracting data from {len(file_ids)} files: {file_ids}")

        if not file_ids:
            logger.error("No file IDs provided for extraction.")
            return {"error": "No files provided"}

        # Construct Schema String
        schema_str = json.dumps(self.target_schema, indent=2)

        # Construct Prompt
        prompt = f"""
You are an expert data extraction assistant.
Please extract information from the attached files and populate the following JSON schema.

RULES:
1. Extract as much data as possible from ALL attached files.
2. AGGREGATE information from all files.
3. If fields allow "self" and "spouse", try to identify primary vs spouse.
4. Merge lists (like participants, accounts) if multiple files contain them.
5. If data is missing, leave as null or empty string as per schema default.
6. Return a JSON object with two top-level keys:
   - "populated_schema": The fully filled schema matching the target structure below.
   - "issues": A list of strings describing any ambiguities, missing critical info, or conflicting data found.

TARGET SCHEMA:
{schema_str}
"""

        try:
            # Construct content list
            content_list = []
            for fid in file_ids:
                content_list.append({"type": "input_file", "file_id": fid})

            content_list.append({"type": "input_text", "text": prompt})

            logger.info("Sending request to OpenAI Responses API...")

            # Call Responses API
            # Note: Using the exact syntax from simple_main.py that worked
            response = self.client.responses.create(
                model=self.config.api.primary_model or "gpt-4o-mini", # Fallback default
                input=[
                    {
                        "role": "user",
                        "content": content_list
                    }
                ]
            )

            # Parse Output
            output_text = response.output_text

            # Clean potential markdown
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]

            extracted_data = json.loads(output_text.strip())

            logger.info("Extraction successful!")
            return extracted_data

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {
                "populated_schema": {},
                "issues": [f"Fatal extraction error: {str(e)}"]
            }

if __name__ == "__main__":
    # Test Extractor with dummy data or previously uploaded files
    pass
