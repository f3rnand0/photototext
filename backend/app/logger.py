import logging
import sys
import uuid
from typing import Any, Dict, Optional
from contextvars import ContextVar

# Context variable to store request ID across async calls
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class RequestIdFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        request_id = request_id_var.get()
        record.request_id = request_id or 'no-request-id'
        return True


class StructuredFormatter(logging.Formatter):
    """Format logs in a structured, readable way."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base message with timestamp and level
        timestamp = self.formatTime(record)
        level = record.levelname
        request_id = getattr(record, 'request_id', 'no-request-id')
        
        # Build the log message
        parts = [
            f"[{timestamp}]",
            f"[{request_id}]",
            f"[{level}]",
            record.getMessage()
        ]
        
        # Add extra context if present
        if hasattr(record, 'context') and record.context:
            context_str = ' | '.join(f"{k}={v}" for k, v in record.context.items())
            parts.append(f"| {context_str}")
        
        # Add exception info if present
        if record.exc_info:
            parts.append(f"\nException: {self.formatException(record.exc_info)}")
        
        return ' '.join(parts)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
        logger.propagate = False
    
    return logger


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set request ID for current context. Returns the ID."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID."""
    return request_id_var.get()


def clear_request_id() -> None:
    """Clear current request ID."""
    request_id_var.set(None)


class log_execution_time:
    """Context manager to log execution time of a block."""
    
    def __init__(self, logger: logging.Logger, operation: str, context: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.operation = operation
        self.context = context or {}
        self.start_time: Optional[float] = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting: {self.operation}", extra={'context': self.context})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type:
                self.logger.error(
                    f"Failed: {self.operation} after {duration:.2f}s",
                    exc_info=(exc_type, exc_val, exc_tb),
                    extra={'context': {**self.context, 'duration_seconds': duration}}
                )
            else:
                self.logger.info(
                    f"Completed: {self.operation} in {duration:.2f}s",
                    extra={'context': {**self.context, 'duration_seconds': duration}}
                )


# Default logger instance
logger = get_logger("photototext")
