"""File-based LLM response cache for eval runs (issue #19).

Enabled only when ``EVAL_CACHE=1``; keyed by ``sha256(prompt + model)``.
The cache lives in ``artifacts/.llm_cache/`` which is gitignored, so live
eval re-runs never repeat paid LLM calls.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

CACHE_DIR = Path("artifacts") / ".llm_cache"


def cache_enabled() -> bool:
    return os.environ.get("EVAL_CACHE", "") == "1"


def _key(prompt: str, model: str) -> str:
    return hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()


def cache_get(prompt: str, model: str) -> str | None:
    path = CACHE_DIR / f"{_key(prompt, model)}.json"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def cache_set(prompt: str, model: str, payload: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # validate before storing so a corrupt write never poisons the cache
    json.loads(payload)
    (CACHE_DIR / f"{_key(prompt, model)}.json").write_text(payload, encoding="utf-8")


__all__ = ["CACHE_DIR", "cache_enabled", "cache_get", "cache_set"]
