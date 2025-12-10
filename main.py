"""
Main Orchestrator - AI-Powered Client Onboarding System

This is the main entry point that orchestrates the entire document processing
and schema population pipeline using OpenAI Files API.

Author: Filippenko Ihor
Date: 2025-12-10
"""

import argparse
import logging
import sys
import time
import os
from pathlib import Path
from typing import Dict, Any, List

from config import get_config
from document_processor import DocumentProcessor
from extractor import Extractor
from validator import Validator
from utils import load_json, save_json

logger = logging.getLogger(__name__)


class ClientOnboardingSystem:
    """
    Main system orchestrator for AI-powered client onboarding.

    Coordinates the full pipeline:
    1. Document uploading/prep (OpenAI Files API)
    2. Information extraction & Schema population (OpenAI Responses API)
    3. Validation and issue detection
    4. Output generation
    """

    def __init__(self, target_schema: Dict[str, Any]):
        """
        Initialize the onboarding system.

        Args:
            target_schema: Target client profile schema
        """
        self.target_schema = target_schema
        self.config = get_config()

        # Initialize components
        self.document_processor = DocumentProcessor()
        # Extractor now takes the schema directly
        self.extractor = Extractor(target_schema)
        self.validator = Validator()

        logger.info("Client onboarding system initialized")

    def process_documents(
        self,
        output_path: Path,
        input_path: Path = None,
        explicit_file_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process documents and generate client profile.

        Args:
            output_path: Path for output JSON file
            input_path: Optional path to directory/file to process
            explicit_file_ids: Optional list of known OpenAI File IDs


        Returns:
            Final results dictionary
        """
        start_time = time.time()

        logger.info(f"{'='*60}")
        logger.info("AI-POWERED CLIENT ONBOARDING SYSTEM")
        logger.info(f"{'='*60}")
        if input_path:
            logger.info(f"Input Path: {input_path}")
        if explicit_file_ids:
            logger.info(f"Explicit File IDs: {explicit_file_ids}")
        logger.info(f"Output: {output_path}")
        logger.info("")

        # Step 1: Document Processing (Upload/Identify Files)
        logger.info("STEP 1/3: Preparing Documents")
        logger.info("-" * 60)

        file_ids = []
        
        # Add explicit IDs first
        if explicit_file_ids:
            file_ids.extend(explicit_file_ids)

        # Process local files if provided
        if input_path:
            if input_path.is_dir():
                doc_results = self.document_processor.process_directory(input_path)
            else:
                doc_result = self.document_processor.process_document(input_path)
                doc_results = [doc_result]

            # Collect valid File IDs from uploads
            uploaded_ids = [r['file_id'] for r in doc_results if r.get('success') and r.get('file_id')]
            file_ids.extend(uploaded_ids)
        
        logger.info(f"✓ Prepared {len(file_ids)} documents for processing (Explicit: {len(explicit_file_ids or [])}, Uploaded: {len(file_ids) - len(explicit_file_ids or [])})\n")

        if not file_ids:
            logger.error("No valid documents to process")
            return self._build_error_result("No valid documents found or upload failed")

        # Step 2: Information Extraction & Population
        logger.info("STEP 2/3: Extracting & Populating Schema")
        logger.info("-" * 60)

        extraction_result = self.extractor.extract_from_files(file_ids)

        populated_schema = extraction_result.get('populated_schema', {})
        issues_from_llm = extraction_result.get('issues', [])

        # Convert simple list of strings to issue objects for consistency if needed
        # Or just adapt validator logic. The validator expects dicts.
        formatted_issues = [
            {"type": "llm_flag", "message": issue, "severity": "medium"}
            for issue in issues_from_llm
        ]

        logger.info("✓ Extraction and population complete\n")

        # Step 3: Validation
        logger.info("STEP 3/3: Validating Results")
        logger.info("-" * 60)

        # Generate simplified metadata for validator
        metadata = self._generate_metadata(populated_schema)

        validation_result = self.validator.validate(
            populated_schema=populated_schema,
            target_schema=self.target_schema,
            metadata=metadata,
            existing_issues=formatted_issues
        )

        logger.info(
            f"✓ Validation {'PASSED' if validation_result['is_valid'] else 'FAILED'} "
            f"with {len(validation_result['all_issues'])} issues detected\n"
        )

        # Step 4: Generate Output
        final_result = self._build_final_result(
            populated_schema=populated_schema,
            metadata=metadata,
            validation_result=validation_result,
            processing_time=time.time() - start_time
        )

        # Verify and clean final result
        if final_result.get('client_profile'):
            final_result['client_profile'] = self._remove_empty_fields(final_result['client_profile'])

        # Save to file
        save_json(final_result, output_path)

        logger.info(f"✓ Results saved to {output_path}\n")

        # Print summary
        self._print_summary(final_result)

        return final_result

    def _generate_metadata(self, data: Any, path: str = "") -> Dict[str, Any]:
        """
        Generate simple metadata (presence/confidence) for the validator.
        Assumes confidence=1.0 for present fields as the Files API doesn't return per-field confidence.
        """
        metadata = {}
        if isinstance(data, dict):
            for k, v in data.items():
                curr_path = f"{path}.{k}" if path else k
                if isinstance(v, (dict, list)):
                     # Recurse
                     metadata.update(self._generate_metadata(v, curr_path))
                else:
                    # Leaf node (or primitive)
                    has_value = v not in (None, "", [], {})
                    metadata[curr_path] = {
                        "has_value": has_value,
                        "confidence": 1.0 if has_value else 0.0 # Dummy confidence
                    }
        elif isinstance(data, list):
             # For simpler prototype validation, we might not track every array item index in metadata keys
             # but let's try to be reasonably granular if possible, or just skip arrays in metadata map
             pass

        return metadata

    def _build_final_result(
        self,
        populated_schema: Dict[str, Any],
        metadata: Dict[str, Any],
        validation_result: Dict[str, Any],
        processing_time: float
    ) -> Dict[str, Any]:
        """Build the final output result."""
        return {
            "client_profile": populated_schema,
            "field_metadata": metadata, # Optional, simplified
            "issues_for_review": validation_result['all_issues'],
            "validation": {
                "is_valid": validation_result['is_valid'],
                "statistics": validation_result['statistics']
            },
            "processing_info": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_time_seconds": round(processing_time, 2),
                "model_used": self.config.api.primary_model
            }
        }

    def _build_error_result(self, error_message: str) -> Dict[str, Any]:
        """Build an error result when processing fails."""
        return {
            "client_profile": self.target_schema,
            "field_metadata": {},
            "issues_for_review": [
                {
                    "type": "fatal_error",
                    "severity": "critical",
                    "message": error_message
                }
            ],
            "validation": {
                "is_valid": False,
                "statistics": {}
            },
            "processing_info": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": error_message
            }
        }

    def _remove_empty_fields(self, data: Any) -> Any:
        """Recursively remove empty fields."""
        if isinstance(data, dict):
            return {
                k: v for k, v in (
                    (k, self._remove_empty_fields(v)) for k, v in data.items()
                )
                if v not in (None, "", [], {})
            }
        elif isinstance(data, list):
            return [
                v for v in (self._remove_empty_fields(item) for item in data)
                if v not in (None, "", [], {})
            ]
        else:
            return data

    def _print_summary(self, result: Dict[str, Any]) -> None:
        """Print a summary of the results to console."""
        logger.info(f"{'='*60}")
        logger.info("PROCESSING SUMMARY")
        logger.info(f"{'='*60}")

        stats = result['validation']['statistics']

        logger.info(f"Population Rate: {stats.get('population_rate', 0)*100:.1f}%")
        logger.info(f"Total Issues: {stats.get('total_issues', 0)}")
        logger.info("")

        issues = result['issues_for_review']
        if issues:
            logger.info("Key Issues:")
            for issue in issues[:5]: # Show top 5
                msg = issue.get('message', str(issue))
                logger.info(f"  - {msg}")
            if len(issues) > 5:
                logger.info(f"  ... and {len(issues) - 5} more")

        logger.info("")
        logger.info(f"Processing Time: {result['processing_info']['processing_time_seconds']}s")
        logger.info(f"{'='*60}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI-Powered Client Onboarding System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--input',
        type=Path,
        required=False,
        help='Input directory or file path (optional if --file-ids provided)'
    )

    parser.add_argument(
        '--file-ids',
        nargs='+',
        help='List of existing OpenAI File IDs to process'
    )

    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output JSON file path'
    )

    parser.add_argument(
        '--schema',
        type=Path,
        default=Path('schema.json'),
        help='Target schema JSON file (default: schema.json)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    parser.add_argument(
        '--api-key',
        type=str,
        help='OpenAI API Key (overrides OPENAI_API_KEY env var)'
    )

    args = parser.parse_args()

    # Set API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key

    # Setup logging
    # Force reload config to pick up any env var changes
    config = get_config(reload=True)
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        config.setup_logging()

    try:
        # Validate configuration explicitly
        config.validate()
        
        # Validate inputs - ensure at least one source is provided
        if not args.input and not args.file_ids:
            logger.error("Error: Must provide either --input or --file-ids")
            sys.exit(1)

        if args.input and not args.input.exists():
            logger.error(f"Input path does not exist: {args.input}")
            sys.exit(1)

        if not args.schema.exists():
            logger.error(f"Schema file does not exist: {args.schema}")
            sys.exit(1)

        # Load target schema
        target_schema = load_json(args.schema)

        # Initialize and run system
        system = ClientOnboardingSystem(target_schema)
        result = system.process_documents(
            output_path=args.output,
            input_path=args.input,
            explicit_file_ids=args.file_ids
        )

        # Exit with appropriate code
        if result['validation']['is_valid']:
            logger.info("✓ Processing completed successfully")
            sys.exit(0)
        else:
            logger.warning("⚠ Processing completed with validation issues")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\nProcess interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
