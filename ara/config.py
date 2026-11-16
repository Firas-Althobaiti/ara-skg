"""Configuration settings for the ARA‑SKG package."""

from __future__ import annotations

from pydantic import BaseSettings, Field, ValidationError
from typing import Literal, Optional


class Settings(BaseSettings):
    """All configuration values are read from environment variables."""

    # LLM settings (optional – can be overridden per‑tier)
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")

    # Neo4j connection
    NEO4J_URI: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="", env="NEO4J_PASSWORD")

    # Vector store location (Chroma by default)
    VECTOR_DIR: str = Field(default="./vector_store", env="VECTOR_DIR")

    # LangChain / LangSmith tracing (optional)
    LANGCHAIN_TRACING_V2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    LANGCHAIN_API_KEY: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    LANGSMITH_PROJECT: str = Field(default="ara-skg", env="LANGSMITH_PROJECT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    @lru_cache(maxsize=1)
    def get_settings(cls) -> "Settings":
        """Cached singleton – ensures settings are created only once."""
        return cls()


def get_settings() -> Settings:
    """Convenient accessor used throughout the codebase."""
    return Settings.get_settings()
