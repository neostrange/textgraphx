"""Central logging configurator for the project.

Usage:
    from textgraphx.logging_config import configure_logging
    configure_logging(level="INFO")

This sets a sane default formatting and can be imported by scripts/tests to
initialize logging consistently.
"""
from __future__ import annotations
import logging
from typing import Optional
import os
import json
from logging.handlers import TimedRotatingFileHandler

from textgraphx.config import get_config


def configure_logging(level: Optional[str] = None) -> None:
    """Configure root logging for the project.

    Args:
        level: optional logging level name or numeric level. Defaults to INFO.
    """
    # Prefer values from the central config, but preserve the ability to
    # override via explicit `level` argument or environment variables.
    cfg = get_config()
    env_level = os.getenv("TEXTGRAPHX_LOG_LEVEL")
    env_json = os.getenv("TEXTGRAPHX_LOG_JSON")
    env_file = os.getenv("TEXTGRAPHX_LOG_FILE")

    if level is None:
        level = env_level or cfg.logging.level or "INFO"
    numeric = level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO)

    use_json = cfg.logging.json
    if env_json is not None:
        # env var explicitly set -> respect it
        use_json = env_json.lower() in ("1", "true", "yes")

    if use_json:
        # Use python-json-logger if available to produce stable JSON logs
        try:
            from pythonjsonlogger import jsonlogger

            logging.basicConfig(level=numeric)
            handler = logging.StreamHandler()
            handler.setLevel(numeric)
            fmt = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
            handler.setFormatter(fmt)
            logging.getLogger().handlers = [handler]
        except Exception:
            # fallback to a simple line-oriented JSON output to stay dependency-free
            logging.basicConfig(level=numeric)
            handler = logging.StreamHandler()
            handler.setLevel(numeric)
            def emit_json(record):
                record.asctime = logging.Formatter().formatTime(record)
                handler.stream.write(json.dumps({
                    "ts": record.asctime,
                    "level": record.levelname,
                    "module": record.name,
                    "msg": record.getMessage()
                }) + "\n")
            handler.emit = emit_json
            logging.getLogger().handlers = [handler]
    else:
        logging.basicConfig(level=numeric, format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s")

    # optional file output with daily rotation
    file_path = cfg.logging.file
    if env_file:
        file_path = env_file

    if file_path:
        fh = TimedRotatingFileHandler(file_path, when="midnight", backupCount=7)
        fh.setLevel(numeric)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s"))
        logging.getLogger().addHandler(fh)

    # Optional per-module level override via env var. Format: "pkg.module=DEBUG,other=INFO"
    env_levels = os.getenv("TEXTGRAPHX_LOG_LEVELS")
    if env_levels:
        for pair in env_levels.split(','):
            if '=' not in pair:
                continue
            name, lvl = pair.split('=', 1)
            name = name.strip()
            lvl = lvl.strip().upper()
            try:
                logging.getLogger(name).setLevel(getattr(logging, lvl))
            except Exception:
                # ignore bad values
                continue