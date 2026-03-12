"""Logging setup utility."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logger(log_level: str, output_dir: Path) -> logging.Logger:
    """Build a logger writing both to terminal and run log file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "simulation.log"

    logger = logging.getLogger("vasociety")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger
