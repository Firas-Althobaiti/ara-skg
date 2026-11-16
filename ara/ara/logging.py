import structlog
from typing import Any

def get_logger(name: str = "ara") -> Any:
    """Return a structured logger bound to the given name."""
    return structlog.get_logger(name).bind()
