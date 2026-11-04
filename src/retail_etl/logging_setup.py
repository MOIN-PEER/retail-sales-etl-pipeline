"""Logging to both the console and a rotating file in logs/."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging(log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("retail_etl")
    root.setLevel(level.upper())
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(LOG_FORMAT, "%H:%M:%S"))
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / "pipeline.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(file_handler)
    return root
