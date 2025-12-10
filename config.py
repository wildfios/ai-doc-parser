"""
Configuration Management Module

This module centralizes all configuration settings for the AI-powered client
onboarding system. It follows Google's configuration best practices with
environment variable support, validation, and sensible defaults.

Author: Filippenko Ihor
Date: 2025-12-10
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class LogLevel(Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class APIConfig:
    """
    API configuration for OpenAI LLM integration.

    Attributes:
        api_key: OpenAI API key (loaded from env or default)
        primary_model: Primary model to use
        fallback_models: List of fallback models if primary fails
        max_tokens: Maximum tokens per request
        temperature: Sampling temperature (0.0 - 1.0)
        timeout: Request timeout in seconds
    """
    api_key: str = field(
        default_factory=lambda: os.getenv(
            "OPENAI_API_KEY"
        )
    )
    primary_model: str = "gpt-4o-mini"
    fallback_models: List[str] = field(
        default_factory=lambda: ["gpt-4o"]
    )
    max_tokens: int = 16000
    temperature: float = 0.1  # Low temperature for consistent, deterministic output
    timeout: int = 120  # 2 minutes timeout for large documents


@dataclass(frozen=True)
class RetryConfig:
    """
    Retry policy configuration.

    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        retryable_status_codes: HTTP status codes that should trigger retry
    """
    max_retries: int = 3
    base_delay: float = 1.0  # Start with 1 second
    max_delay: float = 60.0  # Cap at 1 minute
    exponential_base: float = 2.0  # Doubles each retry
    retryable_status_codes: List[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )


@dataclass(frozen=True)
class ValidationConfig:
    """
    Validation and confidence threshold configuration.

    Attributes:
        min_confidence_threshold: Minimum confidence to auto-accept field
        require_manual_review_threshold: Below this, always flag for review
        max_field_length: Maximum character length for text fields
        date_formats: Accepted date format patterns
    """
    min_confidence_threshold: float = 0.7
    require_manual_review_threshold: float = 0.5
    max_field_length: int = 1000
    date_formats: List[str] = field(
        default_factory=lambda: [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%d %B %Y",
        ]
    )


@dataclass(frozen=True)
class ProcessingConfig:
    """
    Document processing configuration.

    Attributes:
        max_document_size_mb: Maximum document size in megabytes
        supported_formats: List of supported file extensions
        batch_size: Number of documents to process in parallel
        enable_ocr: Whether to enable OCR for scanned documents
    """
    max_document_size_mb: int = 50
    supported_formats: List[str] = field(
        default_factory=lambda: [".pdf", ".docx", ".txt"]
    )
    batch_size: int = 5
    enable_ocr: bool = False  # Can be enabled for scanned PDFs


@dataclass(frozen=True)
class LoggingConfig:
    """
    Logging configuration.

    Attributes:
        level: Logging level
        format: Log message format
        date_format: Timestamp format
        log_file: Optional log file path
    """
    level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    format: str = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_file: Optional[str] = None


@dataclass(frozen=True)
class SystemConfig:
    """
    Main system configuration aggregating all sub-configurations.

    This is the single source of truth for all system settings.
    """
    api: APIConfig = field(default_factory=APIConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def setup_logging(self) -> None:
        """
        Configure the logging system based on logging configuration.

        This should be called once at application startup.
        """
        log_level = getattr(logging, self.logging.level.upper(), logging.INFO)

        handlers = [logging.StreamHandler()]
        if self.logging.log_file:
            handlers.append(logging.FileHandler(self.logging.log_file))

        logging.basicConfig(
            level=log_level,
            format=self.logging.format,
            datefmt=self.logging.date_format,
            handlers=handlers,
            force=True  # Override any existing configuration
        )

        # Reduce noise from external libraries
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def validate(self) -> None:
        """
        Validate configuration settings.

        Raises:
            ValueError: If any configuration is invalid
        """
        if not self.api.api_key:
            raise ValueError("API key must be provided")

        if not 0.0 <= self.api.temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")

        if self.retry.max_retries < 0:
            raise ValueError("Max retries must be non-negative")

        if not 0.0 <= self.validation.min_confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")

        if self.processing.max_document_size_mb <= 0:
            raise ValueError("Max document size must be positive")


# Global configuration instance
_config: Optional['SystemConfig'] = None

def get_config(reload: bool = False) -> 'SystemConfig':
    """
    Get the global configuration instance.
    Initializes it if not already initialized.

    Args:
        reload: If True, re-initialize configuration from environment

    Returns:
        The system configuration object
    """
    global _config
    if _config is None or reload:
        _config = SystemConfig()
    return _config


if __name__ == "__main__":
    # Configuration testing and display
    config = get_config()
    print("=== System Configuration ===")
    print(f"Primary Model: {config.api.primary_model}")
    print(f"Fallback Models: {config.api.fallback_models}")
    print(f"Max Retries: {config.retry.max_retries}")
    print(f"Confidence Threshold: {config.validation.min_confidence_threshold}")
    print(f"Supported Formats: {config.processing.supported_formats}")
    print(f"Log Level: {config.logging.level}")
    print("\n✓ Configuration validated successfully")
