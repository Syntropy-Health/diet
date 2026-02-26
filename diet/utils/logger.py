#!/usr/bin/env python3
"""
Logger Configuration Module

Provides centralized logging configuration for the Diet Insight Engine.
Supports file logging, console output, and structured logging.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_level: str = "DEBUG",
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Set up and configure a logger with file and console handlers.

    Args:
        name: Logger name (typically the module or pipeline name)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        log_dir: Directory for log files
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )

    # Set up file handler if requested
    if log_to_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_path / f"{name}_{timestamp}.log"

        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    # Set up console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_pipeline_logger(pipeline_name: str, log_level: str = None) -> logging.Logger:
    """
    Get a logger specifically configured for pipeline execution with Hydra config.

    Args:
        pipeline_name: Name of the pipeline (e.g., 'die_pipeline', 'symptom_analysis')
        log_level: Optional log level override

    Returns:
        Configured pipeline logger
    """
    # Try to get configuration from Hydra
    try:
        # Use config_manager for logging config
        from diet.utils.config_manager import get_config_manager

        config = get_config_manager().config
        environment = config.get("environment", "development")
        logging_config = config.get("logging", {})
        # Get log level from config if available
        # Force DEBUG for all pipeline loggers for debugging
        log_level = "DEBUG"
        # Get log dir
        log_dir = logging_config.get("file", {}).get("path", "logs")
        # Get file and console logging settings
        file_config = logging_config.get("file", {})
        console_config = logging_config.get("console", {})
        return setup_logger(
            name=pipeline_name,
            log_level=log_level,
            log_to_file=file_config.get("enabled", True),
            log_to_console=console_config.get("enabled", True),
            log_dir=log_dir,
            max_bytes=file_config.get("rotation", {}).get("max_bytes", 10485760),
            backup_count=file_config.get("rotation", {}).get("backup_count", 5),
        )
    except Exception as e:
        # Fallback to environment variables or defaults
        print(f"Warning: Could not load Hydra config for logging: {e}")
        if log_level is None:
            log_level = os.getenv("LOG_LEVEL", "INFO")

        return setup_logger(
            name=pipeline_name,
            log_level=log_level,
            log_to_file=True,
            log_to_console=True,
            log_dir="logs",
        )


def setup_logging_for_demo(scenario: str = "general") -> logging.Logger:
    """Set up logging specifically for demo runs."""
    return setup_logger(
        name=f"demo_{scenario}",
        log_level="INFO",
        log_to_file=True,
        log_to_console=True,
        log_dir="logs",
    )


class StructuredLogger:
    """
    Structured logger for consistent logging across the application.
    Provides context-aware logging with structured data.
    """

    def __init__(self, name: str, log_level: str = "INFO"):
        self.logger = get_pipeline_logger(name, log_level)
        self.context = {}

    def set_context(self, **kwargs):
        """Set context information that will be included in all log messages."""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all context information."""
        self.context.clear()

    def _format_message(self, message: str, extra_context: dict = None) -> str:
        """Format message with context information."""
        context = {**self.context}
        if extra_context:
            context.update(extra_context)

        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            return f"{message} | {context_str}"
        return message

    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self.logger.debug(self._format_message(message, kwargs))

    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self.logger.info(self._format_message(message, kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self.logger.warning(self._format_message(message, kwargs))

    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self.logger.error(self._format_message(message, kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self.logger.critical(self._format_message(message, kwargs))


# Convenience functions for quick logger setup
def get_logger(name: str) -> logging.Logger:
    """Get a standard logger for the given name."""
    return get_pipeline_logger(name)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger for the given name."""
    return StructuredLogger(name)
