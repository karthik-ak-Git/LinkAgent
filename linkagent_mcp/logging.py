"""
Structured logging setup for LinkAgent MCP.

Provides a configured logger with optional file output and structured formatting.

Usage:
    from linkagent_mcp.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Server started", extra={"port": 9222})
"""

import logging
import sys
from typing import Optional

_configured = False


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional file path to write logs to.
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger("linkagent")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stderr handler (always)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    # file handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger under the linkagent namespace.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(f"linkagent.{name}")
