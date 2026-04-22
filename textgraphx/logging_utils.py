"""Enhanced logging utilities for textgraphx project.

Provides:
- Structured logging with context
- Performance timing decorators
- Component loggers with consistent formatting
- Debug/trace utilities
"""

import logging
import functools
import time
from typing import Optional, Callable, Any
from contextlib import contextmanager
import sys
from pathlib import Path


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def __init__(self, context: Optional[dict] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    # Ensure logger has handlers (in case configure_logging wasn't called)
    if not logger.handlers and not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
        )
    return logger


def timer_log(name: str = "", level: int = logging.INFO) -> Callable:
    """Decorator to log function execution time.
    
    Args:
        name: Optional name for the operation (defaults to function name)
        level: Logging level (default: INFO)
    
    Examples:
        @timer_log("database_query")
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)
            op_name = name or func.__name__
            
            logger.log(level, f"▶ Starting: {op_name}")
            start = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.log(level, f"✓ Completed: {op_name} ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"✗ Failed: {op_name} ({elapsed:.2f}s) - {type(e).__name__}: {e}")
                raise
        
        return wrapper
    return decorator


def debug_log(msg: str = "", level: int = logging.DEBUG) -> Callable:
    """Decorator to log function calls with arguments and returns.
    
    Args:
        msg: Optional custom message
        level: Logging level (default: DEBUG)
    
    Examples:
        @debug_log()
        def process_data(doc_id, count):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)
            func_name = func.__name__
            custom_msg = msg or ""
            
            # Format arguments (hide sensitive ones)
            arg_strs = [repr(arg) for arg in args if arg is not None]
            kwarg_strs = [f"{k}={repr(v)}" for k, v in kwargs.items() if v is not None]
            args_display = ", ".join(arg_strs + kwarg_strs)
            
            if custom_msg:
                logger.log(level, f"🔍 {custom_msg} → {func_name}({args_display})")
            else:
                logger.log(level, f"🔍 {func_name}({args_display})")
            
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"🔙 {func_name} → {type(result).__name__}")
                return result
            except Exception as e:
                logger.log(logging.ERROR, f"🔙 {func_name} raised {type(e).__name__}")
                raise
        
        return wrapper
    return decorator


@contextmanager
def log_section(logger: logging.Logger, section_name: str, level: int = logging.INFO):
    """Context manager for logging a section of code.
    
    Args:
        logger: Logger instance
        section_name: Name of the section
        level: Logging level
    
    Examples:
        with log_section(logger, "Database Migration"):
            migrate_tables()
    """
    logger.log(level, f"\n{'='*60}")
    logger.log(level, f"▶ {section_name}")
    logger.log(level, f"{'='*60}")
    
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.log(level, f"✓ {section_name} completed in {elapsed:.2f}s")
        logger.log(level, f"{'='*60}\n")


@contextmanager
def log_subsection(logger: logging.Logger, section_name: str, level: int = logging.INFO):
    """Context manager for logging a subsection of code.
    
    Args:
        logger: Logger instance
        section_name: Name of the subsection
        level: Logging level
    
    Examples:
        with log_subsection(logger, "Extracting entities"):
            extract_entities()
    """
    logger.log(level, f"\n  ⟶ {section_name}...")
    
    start = time.time()
    try:
        yield logger
    finally:
        elapsed = time.time() - start
        logger.log(level, f"  ✓ {section_name} ({elapsed:.2f}s)")


class ProgressLogger:
    """Helper for logging progress through a process."""
    
    def __init__(self, logger: logging.Logger, total: int, name: str = "Processing"):
        self.logger = logger
        self.total = total
        self.name = name
        self.count = 0
        self._last_percent = 0
    
    def update(self, count: int = 1, message: str = ""):
        """Update progress.
        
        Args:
            count: Number of items processed (default: 1)
            message: Optional message to log
        """
        self.count += count
        if self.total > 0:
            percent = int((self.count / self.total) * 100)
            
            # Log at each 10% increment
            if percent >= self._last_percent + 10:
                self.logger.info(f"  {self.name}: {self.count}/{self.total} ({percent}%)")
                self._last_percent = percent
            
            if message:
                self.logger.debug(f"    {message}")
    
    def finish(self):
        """Log completion."""
        self.logger.info(f"  {self.name}: {self.count}/{self.total} (100%)")


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """Log an exception with full details.
    
    Args:
        logger: Logger instance
        exc: Exception to log
        context: Optional context message
    """
    msg = f"Exception in {context}" if context else "Exception occurred"
    logger.exception(f"{msg}: {type(exc).__name__}: {exc}")


def setup_component_logging(component_name: str, level: Optional[str] = None) -> logging.Logger:
    """Setup logging for a component with optional file output.
    
    Args:
        component_name: Name of the component (e.g., "GraphBasedNLP")
        level: Optional log level override
    
    Returns:
        Configured logger for the component
    """
    logger = get_logger(f"textgraphx.{component_name}")
    
    if level:
        numeric_level = getattr(logging, str(level).upper(), logging.INFO)
        logger.setLevel(numeric_level)
    
    # Add file handler for this component if not already present
    has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    if not has_file_handler:
        log_dir = Path.home() / ".textgraphx_logs"
        log_dir.mkdir(exist_ok=True)
        
        file_path = log_dir / f"{component_name.lower()}.log"
        fh = logging.FileHandler(file_path)
        fh.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        logger.debug(f"Component logger {component_name} initialized. Log file: {file_path}")
    
    return logger
