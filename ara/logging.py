"""Structured logging helper."""

from typing import Any

import structlog


def get_logger(name: str = "ara") -> Any:
    """
    Return a structured logger bound to *name*.

    The logger can be used as:

    >>> log = get_logger("my_component")
    >>> log.info("something happened")
    """
    return structlog.get_logger(name)
