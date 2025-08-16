"""Logging utilities for MetaCLI."""

import logging
import sys
from pathlib import Path
from typing import Optional


# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logger(verbose: bool = False, log_file: str = 'metacli.log') -> logging.Logger:
    """Set up and configure the application logger.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        log_file: Path to log file
        
    Returns:
        Configured logger instance
    """
    global _logger
    
    # Create logger
    logger = logging.getLogger('metacli')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler - always detailed
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    except Exception:
        # If file logging fails, continue without it
        pass
    
    # Console handler - only for errors and warnings unless verbose
    console_handler = logging.StreamHandler(sys.stderr)
    
    if verbose:
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(detailed_formatter)
    else:
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(simple_formatter)
    
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """Get the application logger instance.
    
    Returns:
        Logger instance (creates default if none exists)
    """
    global _logger
    
    if _logger is None:
        _logger = setup_logger()
    
    return _logger


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger instance for this class."""
        return get_logger()


def log_function_call(func):
    """Decorator to log function calls in debug mode."""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.debug(f"{func.__name__} failed with error: {e}")
            raise
    
    return wrapper


class ProgressLogger:
    """Logger for progress tracking."""
    
    def __init__(self, total: int, description: str = "Processing"):
        """Initialize progress logger.
        
        Args:
            total: Total number of items to process
            description: Description of the operation
        """
        self.total = total
        self.current = 0
        self.description = description
        self.logger = get_logger()
        
        self.logger.info(f"Starting {description}: {total} items")
    
    def update(self, increment: int = 1) -> None:
        """Update progress.
        
        Args:
            increment: Number of items processed
        """
        self.current += increment
        
        if self.current % max(1, self.total // 10) == 0 or self.current == self.total:
            percent = (self.current / self.total) * 100
            self.logger.info(f"{self.description}: {self.current}/{self.total} ({percent:.1f}%)")
    
    def complete(self) -> None:
        """Mark progress as complete."""
        self.logger.info(f"{self.description} completed: {self.current}/{self.total} items")


class ErrorCollector:
    """Collect and manage errors during batch operations."""
    
    def __init__(self):
        """Initialize error collector."""
        self.errors = []
        self.logger = get_logger()
    
    def add_error(self, item: str, error: Exception) -> None:
        """Add an error to the collection.
        
        Args:
            item: Item that caused the error
            error: The exception that occurred
        """
        error_info = {
            'item': item,
            'error': str(error),
            'type': type(error).__name__
        }
        
        self.errors.append(error_info)
        self.logger.warning(f"Error processing {item}: {error}")
    
    def has_errors(self) -> bool:
        """Check if any errors were collected.
        
        Returns:
            True if errors exist
        """
        return len(self.errors) > 0
    
    def get_error_count(self) -> int:
        """Get the number of errors collected.
        
        Returns:
            Number of errors
        """
        return len(self.errors)
    
    def get_errors(self) -> list:
        """Get all collected errors.
        
        Returns:
            List of error dictionaries
        """
        return self.errors.copy()
    
    def log_summary(self) -> None:
        """Log a summary of all errors."""
        if not self.errors:
            return
        
        self.logger.error(f"Total errors encountered: {len(self.errors)}")
        
        # Group errors by type
        error_types = {}
        for error in self.errors:
            error_type = error['type']
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(error)
        
        for error_type, errors in error_types.items():
            self.logger.error(f"  {error_type}: {len(errors)} occurrences")
            
            # Log first few examples
            for i, error in enumerate(errors[:3]):
                self.logger.error(f"    Example {i+1}: {error['item']} - {error['error']}")
            
            if len(errors) > 3:
                self.logger.error(f"    ... and {len(errors) - 3} more")
    
    def clear(self) -> None:
        """Clear all collected errors."""
        self.errors.clear()