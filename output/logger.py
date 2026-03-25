"""
desktop_agent.output.logger
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Centralized logging configuration with rotating file handler and
coloured console output.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)


class _ColorFormatter(logging.Formatter):
    """Console formatter that adds color codes by log level."""

    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, "")
        reset = Style.RESET_ALL
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


def setup_logging(config: dict[str, Any]) -> None:
    """Configure the root logger from *config['logging']*."""
    log_cfg = config.get("logging", {})
    level_name = log_cfg.get("level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove any pre‐existing handlers
    root.handlers.clear()

    fmt = "%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # ── Console handler ─────────────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(_ColorFormatter(fmt, datefmt=date_fmt))
    root.addHandler(console)

    # ── File handler (rotating) ─────────────────────────────────────────
    log_file = log_cfg.get("file", "desktop_agent.log")
    max_bytes = log_cfg.get("max_bytes", 5_242_880)
    backup_count = log_cfg.get("backup_count", 3)

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(fmt, datefmt=date_fmt))
    root.addHandler(file_handler)

    logging.getLogger(__name__).info(
        "Logging initialised — level=%s, file=%s", level_name, log_path
    )
