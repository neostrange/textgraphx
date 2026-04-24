"""Enhanced logging utilities for textgraphx project."""

import functools
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""

    def __init__(self, context: Optional[dict] = None):
        super().__init__()
        self.context = context or {}

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for a module."""
    logger = logging.getLogger(name)
    if not logger.handlers and not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
        )
    return logger


def timer_log(name: str = "", level: int = logging.INFO) -> Callable:
    """Decorator to log function execution time."""

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
            except Exception as exc:
                elapsed = time.time() - start
                logger.error(f"✗ Failed: {op_name} ({elapsed:.2f}s) - {type(exc).__name__}: {exc}")
                raise

        return wrapper

    return decorator


def debug_log(msg: str = "", level: int = logging.DEBUG) -> Callable:
    """Decorator to log function calls with arguments and returns."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__)
            func_name = func.__name__
            custom_msg = msg or ""
            arg_strs = [repr(arg) for arg in args if arg is not None]
            kwarg_strs = [f"{key}={repr(value)}" for key, value in kwargs.items() if value is not None]
            args_display = ", ".join(arg_strs + kwarg_strs)
            if custom_msg:
                logger.log(level, f"🔍 {custom_msg} → {func_name}({args_display})")
            else:
                logger.log(level, f"🔍 {func_name}({args_display})")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"🔙 {func_name} → {type(result).__name__}")
                return result
            except Exception as exc:
                logger.log(logging.ERROR, f"🔙 {func_name} raised {type(exc).__name__}")
                raise

        return wrapper

    return decorator


@contextmanager
def log_section(logger: logging.Logger, section_name: str, level: int = logging.INFO):
    """Context manager for logging a section of code."""
    logger.log(level, f"\n{'=' * 60}")
    logger.log(level, f"▶ {section_name}")
    logger.log(level, f"{'=' * 60}")
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        logger.log(level, f"✓ {section_name} completed in {elapsed:.2f}s")
        logger.log(level, f"{'=' * 60}\n")


@contextmanager
def log_subsection(logger: logging.Logger, section_name: str, level: int = logging.INFO):
    """Context manager for logging a subsection of code."""
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
        self.count += count
        if self.total > 0:
            percent = int((self.count / self.total) * 100)
            if percent >= self._last_percent + 10:
                self.logger.info(f"  {self.name}: {self.count}/{self.total} ({percent}%)")
                self._last_percent = percent
            if message:
                self.logger.debug(f"    {message}")

    def finish(self):
        self.logger.info(f"  {self.name}: {self.count}/{self.total} (100%)")


def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """Log an exception with full details."""
    msg = f"Exception in {context}" if context else "Exception occurred"
    logger.exception(f"{msg}: {type(exc).__name__}: {exc}")


def setup_component_logging(component_name: str, level: Optional[str] = None) -> logging.Logger:
    """Setup logging for a component with optional file output."""
    logger = get_logger(f"textgraphx.{component_name}")
    if level:
        numeric_level = getattr(logging, str(level).upper(), logging.INFO)
        logger.setLevel(numeric_level)

    has_file_handler = any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
    if not has_file_handler:
        log_dir = Path.home() / ".textgraphx_logs"
        log_dir.mkdir(exist_ok=True)
        file_path = log_dir / f"{component_name.lower()}.log"
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug(f"Component logger {component_name} initialized. Log file: {file_path}")

    return logger


__all__ = [
    "ContextFilter",
    "ProgressLogger",
    "debug_log",
    "get_logger",
    "log_exception",
    "log_section",
    "log_subsection",
    "setup_component_logging",
    "timer_log",
]