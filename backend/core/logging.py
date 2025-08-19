"""
Centralized logging configuration for the LangChef backend.

This module provides a consistent logging setup across all backend modules,
with structured logging, proper formatting, and configurable log levels.
"""

import logging
import logging.config
import sys
from typing import Dict, Any
from pathlib import Path

from backend.config import settings


def get_logging_config() -> Dict[str, Any]:
    """
    Get the logging configuration dictionary.
    
    Returns:
        Dict containing the logging configuration
    """
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s"
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(funcName)s %(lineno)d %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": "logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf8"
            }
        },
        "loggers": {
            # Application loggers
            "backend": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "backend.database": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "backend.services": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "backend.api": {
                "level": log_level,
                "handlers": ["console", "file"],
                "propagate": False
            },
            # Third-party loggers
            "sqlalchemy.engine": {
                "level": "WARN",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "error_file"]
        }
    }
    
    return config


def setup_logging():
    """
    Setup logging configuration for the entire application.
    
    This function should be called once at application startup.
    """
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Apply logging configuration
    config = get_logging_config()
    logging.config.dictConfig(config)
    
    # Get the root logger and log startup message
    logger = logging.getLogger("backend")
    logger.info("Logging configuration initialized")
    logger.info(f"Log level: {'DEBUG' if settings.DEBUG else 'INFO'}")
    logger.info(f"Debug mode: {settings.DEBUG}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: The name for the logger (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("This is a log message")
    """
    return logging.getLogger(name)


# Convenience function for commonly used patterns
def log_function_entry(logger: logging.Logger, func_name: str, **kwargs):
    """Log function entry with parameters."""
    if kwargs:
        logger.debug(f"Entering {func_name} with params: {kwargs}")
    else:
        logger.debug(f"Entering {func_name}")


def log_function_exit(logger: logging.Logger, func_name: str, result=None):
    """Log function exit with optional result."""
    if result is not None:
        logger.debug(f"Exiting {func_name} with result type: {type(result).__name__}")
    else:
        logger.debug(f"Exiting {func_name}")


def log_database_operation(logger: logging.Logger, operation: str, table: str, **kwargs):
    """Log database operations."""
    logger.debug(f"Database {operation} on {table}: {kwargs}")


def log_api_request(logger: logging.Logger, method: str, path: str, user_id: str = None):
    """Log API requests."""
    user_info = f" (user: {user_id})" if user_id else ""
    logger.info(f"API {method} {path}{user_info}")


def log_error_with_context(logger: logging.Logger, error: Exception, context: Dict[str, Any]):
    """Log errors with additional context."""
    logger.error(f"Error: {str(error)} | Context: {context}", exc_info=True)