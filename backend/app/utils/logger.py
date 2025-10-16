"""
Structured JSON logging configuration for HIPAA-compliant audit trails.

This module provides:
- JSON log formatting with structured fields
- Context managers for enriching log records
- Log level configuration based on environment
- HIPAA-compliant logging practices (no PHI in logs)
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Context variables for request-scoped logging context
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
tenant_id_ctx: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs logs in JSON format with:
    - timestamp (ISO 8601)
    - level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger name
    - message
    - request_id, user_id, tenant_id (if available from context)
    - additional context fields
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            str: JSON-formatted log entry
        """
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add request-scoped context if available
        request_id = request_id_ctx.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_ctx.get()
        if user_id:
            log_data["user_id"] = user_id

        tenant_id = tenant_id_ctx.get()
        if tenant_id:
            log_data["tenant_id"] = tenant_id

        # Add additional context from record extras
        if hasattr(record, "context") and isinstance(record.context, dict):
            log_data["context"] = record.context

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add source location for ERROR and CRITICAL logs
        if record.levelno >= logging.ERROR:
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data, default=str)


class LogContext:
    """
    Context manager for enriching log records with request context.

    Usage:
        with LogContext(request_id="req-123", user_id="user-456"):
            logger.info("Processing request")  # Will include request_id and user_id
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """
        Initialize log context.

        Args:
            request_id: Unique request identifier
            user_id: User identifier
            tenant_id: Tenant identifier
        """
        self.request_id = request_id
        self.user_id = user_id
        self.tenant_id = tenant_id

        # Store previous values for restoration
        self._prev_request_id = None
        self._prev_user_id = None
        self._prev_tenant_id = None

    def __enter__(self):
        """Set context variables on entry."""
        if self.request_id:
            self._prev_request_id = request_id_ctx.get()
            request_id_ctx.set(self.request_id)

        if self.user_id:
            self._prev_user_id = user_id_ctx.get()
            user_id_ctx.set(self.user_id)

        if self.tenant_id:
            self._prev_tenant_id = tenant_id_ctx.get()
            tenant_id_ctx.set(self.tenant_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous context variables on exit."""
        if self.request_id:
            request_id_ctx.set(self._prev_request_id)

        if self.user_id:
            user_id_ctx.set(self._prev_user_id)

        if self.tenant_id:
            tenant_id_ctx.set(self._prev_tenant_id)


def setup_logging(log_level: str = "INFO", enable_json: bool = True) -> None:
    """
    Configure application logging.

    Sets up root logger with JSON formatting and appropriate log level.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Whether to use JSON formatting (default: True)
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Set formatter
    if enable_json:
        formatter = JSONFormatter()
    else:
        # Simple formatter for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    root_logger.info(
        f"Logging configured with level: {log_level}, JSON format: {enable_json}"
    )


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log message with additional context.

    Args:
        logger: Logger instance
        level: Log level (logging.DEBUG, logging.INFO, etc.)
        message: Log message
        context: Additional context dictionary
    """
    extra = {"context": context} if context else {}
    logger.log(level, message, extra=extra)


# Convenience functions for logging with context
def debug_with_context(
    logger: logging.Logger,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log debug message with context."""
    log_with_context(logger, logging.DEBUG, message, context)


def info_with_context(
    logger: logging.Logger,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log info message with context."""
    log_with_context(logger, logging.INFO, message, context)


def warning_with_context(
    logger: logging.Logger,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log warning message with context."""
    log_with_context(logger, logging.WARNING, message, context)


def error_with_context(
    logger: logging.Logger,
    message: str,
    context: Optional[Dict[str, Any]] = None,
    exc_info: bool = False,
) -> None:
    """Log error message with context."""
    extra = {"context": context} if context else {}
    logger.error(message, exc_info=exc_info, extra=extra)
