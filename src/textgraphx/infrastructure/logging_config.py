"""Central logging configurator for the project."""

from __future__ import annotations

import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import Optional

from textgraphx.infrastructure.config import get_config


def configure_logging(level: Optional[str] = None) -> None:
    """Configure root logging for the project."""
    cfg = get_config()
    env_level = os.getenv("TEXTGRAPHX_LOG_LEVEL")
    env_json = os.getenv("TEXTGRAPHX_LOG_JSON")
    env_file = os.getenv("TEXTGRAPHX_LOG_FILE")

    if level is None:
        level = env_level or cfg.logging.level or "INFO"
    numeric = level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO)

    use_json = cfg.logging.json
    if env_json is not None:
        use_json = env_json.lower() in ("1", "true", "yes")

    if use_json:
        try:
            from pythonjsonlogger import jsonlogger

            logging.basicConfig(level=numeric)
            handler = logging.StreamHandler()
            handler.setLevel(numeric)
            formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
            handler.setFormatter(formatter)
            logging.getLogger().handlers = [handler]
        except Exception:
            logging.basicConfig(level=numeric)
            handler = logging.StreamHandler()
            handler.setLevel(numeric)

            def emit_json(record):
                record.asctime = logging.Formatter().formatTime(record)
                handler.stream.write(
                    json.dumps(
                        {
                            "ts": record.asctime,
                            "level": record.levelname,
                            "module": record.name,
                            "msg": record.getMessage(),
                        }
                    )
                    + "\n"
                )

            handler.emit = emit_json
            logging.getLogger().handlers = [handler]
    else:
        logging.basicConfig(level=numeric, format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s")

    file_path = cfg.logging.file
    if env_file:
        file_path = env_file

    if file_path:
        file_handler = TimedRotatingFileHandler(file_path, when="midnight", backupCount=7)
        file_handler.setLevel(numeric)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s"))
        logging.getLogger().addHandler(file_handler)

    env_levels = os.getenv("TEXTGRAPHX_LOG_LEVELS")
    if env_levels:
        for pair in env_levels.split(","):
            if "=" not in pair:
                continue
            name, configured_level = pair.split("=", 1)
            name = name.strip()
            configured_level = configured_level.strip().upper()
            try:
                logging.getLogger(name).setLevel(getattr(logging, configured_level))
            except Exception:
                continue


__all__ = ["configure_logging"]