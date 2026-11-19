"""Configuration settings for the ARA‑SKG package."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from ara.clients.kg import KnowledgeGraphClient


class Settings(BaseSettings):  # type: ignore[misc]
    """All configuration values are read from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM settings (optional – can be overridden per‑tier)
    OPENAI_API_KEY: str | None = Field(default=None)

    # Neo4j connection
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="")

    # NCBI E-utilities API key — raises the rate limit from 3 to 10 req/s
    NCBI_API_KEY: str | None = Field(default=None)

    # Entity linking: "noop" (default, names unchanged) or "alias" (dev-only
    # fake alias map, logs a warning — never use in production)
    LINKING_MODE: Literal["noop", "alias"] = Field(default="noop")

    # LLM modes: "mock" (deterministic, CI-safe default) or "live" (real LLM,
    # requires OPENAI_API_KEY; never enabled in CI on push/PR)
    EXTRACTION_MODE: Literal["mock", "live"] = Field(default="mock")
    HYPOTHESIS_MODE: Literal["mock", "live"] = Field(default="mock")

    # Optional override for the OpenAI-compatible endpoint (e.g. a proxy)
    OPENAI_BASE_URL: str | None = Field(default=None)

    # File-cache LLM responses during live evals (keeps cost under the cap)
    EVAL_CACHE: bool = Field(default=False)

    # Knowledge-graph backend: "networkx" (local JSON file, default, offline)
    # or "neo4j" (requires a running Neo4j instance, see docker-compose).
    ARA_KG_BACKEND: str = Field(default="networkx")
    # Storage path used by the NetworkX backend.
    ARA_KG_STORE: str = Field(default="kg_store.json")

    # Vector store location (Chroma by default)
    VECTOR_DIR: str = Field(default="./vector_store")

    # LangChain / LangSmith tracing (optional)
    LANGCHAIN_TRACING_V2: bool = Field(default=True)
    LANGCHAIN_API_KEY: str | None = Field(default=None)
    LANGSMITH_PROJECT: str = Field(default="ara-skg")

    _kg_client: Any = PrivateAttr(default=None)

    @property
    def client(self) -> KnowledgeGraphClient:
        """Knowledge-graph client for the configured backend (lazy, cached).

        Nodes obtain their KG handle via ``get_settings().client`` so tests can
        monkeypatch either this property or ``get_settings`` itself.
        """
        if self._kg_client is None:
            from ara.clients.kg import get_kg_client

            self._kg_client = get_kg_client(self)
        return self._kg_client  # type: ignore[no-any-return]

    @classmethod
    def get_settings(cls) -> Settings:
        """Cached singleton – kept for backwards compatibility."""
        return get_settings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Convenient cached accessor used throughout the codebase.

    Call ``get_settings.cache_clear()`` (e.g. in tests) to re-read the
    environment after changing variables.
    """
    return Settings()
