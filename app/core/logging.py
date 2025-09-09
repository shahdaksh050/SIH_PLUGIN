"""
Structured logging configuration for the TM2 Healthcare Service.

This module sets up structured JSON logging with contextual information
for production monitoring and debugging.
"""

import logging
import logging.config
import sys
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

settings = get_settings()


class HealthcareContextProcessor:
    """
    Custom processor to add healthcare-specific context to log entries.
    """
    
    def __call__(self, logger: Any, name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add healthcare service context to log entries.
        
        Args:
            logger: Logger instance
            name: Logger name
            event_dict: Event dictionary
            
        Returns:
            Dict: Enhanced event dictionary with context
        """
        event_dict.update({
            "service": "tm2-healthcare-service",
            "version": "1.0.0",
            "environment": settings.environment
        })
        return event_dict


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    
    Sets up both standard Python logging and structlog for
    consistent structured logging throughout the application.
    """
    
    # Configure standard library logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json" if settings.environment == "production" else "console",
                "level": settings.log_level
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": settings.log_level,
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        HealthcareContextProcessor(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[structlog.processors.CallsiteParameter.FUNC_NAME]
        ),
    ]
    
    if settings.environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured structlog logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


# Request ID context management
class RequestIDContext:
    """
    Context manager for request ID tracking in logs.
    """
    
    def __init__(self, request_id: str):
        self.request_id = request_id
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(request_id=self.request_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.unbind_contextvars("request_id")


# Healthcare operation context management
class HealthcareOperationContext:
    """
    Context manager for healthcare operation tracking in logs.
    """
    
    def __init__(self, operation: str, patient_id: str = None, record_count: int = None):
        self.operation = operation
        self.patient_id = patient_id
        self.record_count = record_count
    
    def __enter__(self):
        context_vars = {"healthcare_operation": self.operation}
        if self.patient_id:
            context_vars["patient_id"] = self.patient_id
        if self.record_count:
            context_vars["record_count"] = self.record_count
        
        structlog.contextvars.bind_contextvars(**context_vars)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        vars_to_unbind = ["healthcare_operation"]
        if self.patient_id:
            vars_to_unbind.append("patient_id")
        if self.record_count:
            vars_to_unbind.append("record_count")
        
        structlog.contextvars.unbind_contextvars(*vars_to_unbind)