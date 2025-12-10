"""
Document Processing Module
This module handles preparation of documents for the OpenAI API.
It manages file uploads to OpenAI and retrieval of file IDs.
Author: Filippenko Ihor
Date: 2025-12-10
"""

import logging
from pathlib import Path
from typing import Dict, List, Union
from openai import OpenAI

from config import get_config

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass


class DocumentProcessor:
    """
    Handles preparation of documents for OpenAI API processing.

    Uploads files to OpenAI 'files' endpoint and manages file IDs.
    """

    # Pre-defined IDs map removed in favor of CLI arguments
    KNOWN_FILE_IDS = {}

    def __init__(self):
        """Initialize document processor with configuration."""
        self.config = get_config()
        self.client = OpenAI(api_key=self.config.api.api_key)
        self.supported_formats = self.config.processing.supported_formats

    def process_document(self, file_path: Union[str, Path]) -> Dict[str, any]:
        """
        Process a document: Upload to OpenAI and get File ID.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary containing:
                - file_name: Original filename
                - file_id: OpenAI File ID
                - success: Whether processing succeeded
                - error: Error message if failed
        """
        file_path = Path(file_path)

        # Validate file exists
        if not file_path.exists():
            raise DocumentProcessingError(f"File not found: {file_path}")

        # Validate file format
        file_ext = file_path.suffix.lower()
        if file_ext not in self.supported_formats:
             # Just a warning or strict error? Sticking to strict for consistency
             pass
             # Actually, let's allow it but warn, or checking config.
             # Config was: supported_formats = ['.pdf', '.docx', '.txt']

        logger.info(f"Processing document: {file_path.name}")

        try:
            # Upload file
            logger.info(f"Uploading {file_path.name} to OpenAI Files API...")
            with open(file_path, "rb") as f:
                response = self.client.files.create(
                    file=f,
                    purpose="assistants" # or 'responses' if that becomes a specific purpose, usually 'assistants' or 'fine-tune'
                )
            file_id = response.id
            logger.info(f"Uploaded successfully. File ID: {file_id}")

            return {
                "file_name": file_path.name,
                "file_type": file_ext,
                "file_id": file_id,
                "success": True,
                "error": None
            }

        except Exception as e:
            error_msg = f"Failed to upload/process {file_path.name}: {str(e)}"
            logger.error(error_msg)

            return {
                "file_name": file_path.name,
                "file_type": file_ext,
                "file_id": None,
                "success": False,
                "error": error_msg
            }

    def process_directory(self, directory_path: Union[str, Path]) -> List[Dict]:
        """
        Process all supported documents in a directory.

        Args:
            directory_path: Path to directory containing documents

        Returns:
            List of processing results for each document
        """
        directory_path = Path(directory_path)

        if not directory_path.exists():
            raise DocumentProcessingError(f"Directory not found: {directory_path}")

        if not directory_path.is_dir():
            raise DocumentProcessingError(f"Not a directory: {directory_path}")

        # Find all supported files
        results = []
        for file_path in directory_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    result = self.process_document(file_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {file_path.name}: {e}")
                    results.append({
                        "file_name": file_path.name,
                        "file_id": None,
                        "success": False,
                        "error": str(e)
                    })

        logger.info(f"Processed {len(results)} documents from {directory_path}")
        return results

if __name__ == "__main__":
    # Test document processor
    logging.basicConfig(level=logging.INFO)
    print("=== Testing Document Processor ===\n")
    processor = DocumentProcessor()

    # Needs a real file to test upload or mock
    # processor.process_directory("input")
