import pytest
from pydantic import ValidationError

from ara.config import Settings, get_settings


def test_settings_defaults():
    # Clear cache to ensure we read fresh environment variables
    get_settings.cache_clear()
    
    # Ensure the cached singleton returns a Settings instance
    settings = get_settings()
    assert isinstance(settings, Settings)

    # Verify optional fields are None when not set
    assert settings.OPENAI_API_KEY is None
    assert settings.NEO4J_URI == "bolt://localhost:7687"
    assert settings.NEO4J_USER == "neo4j"
    assert settings.NEO4J_PASSWORD == ""
    assert settings.VECTOR_DIR == "./vector_store"
    assert settings.LANGCHAIN_TRACING_V2 is True
    assert settings.LANGCHAIN_API_KEY is None
    assert settings.LANGSMITH_PROJECT == "ara-skg"


def test_settings_env_override(monkeypatch):
    get_settings.cache_clear()  # Clear cache before testing overrides
    
    monkeypatch.setenv("OPENAI_API_KEY", "sk-abc123")
    monkeypatch.setenv("NEO4J_URI", "bolt://neohost:7687")
    monkeypatch.setenv("NEO4J_USER", "admin")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    monkeypatch.setenv("VECTOR_DIR", "/custom/vec")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGCHAIN_API_KEY", "cl-xyz")
    monkeypatch.setenv("LANGSMITH_PROJECT", "my-project")

    settings = get_settings()
    assert settings.OPENAI_API_KEY == "sk-abc123"
    assert settings.NEO4J_URI == "bolt://neohost:7687"
    assert settings.NEO4J_USER == "admin"
    assert settings.NEO4J_PASSWORD == "secret"
    assert settings.VECTOR_DIR == "/custom/vec"
    assert settings.LANGCHAIN_TRACING_V2 is False
    assert settings.LANGCHAIN_API_KEY == "cl-xyz"
    assert settings.LANGSMITH_PROJECT == "my-project"


def test_missing_required_env(monkeypatch):
    get_settings.cache_clear()
    
    # Remove a required env var (NEO4J_URI) and ensure Settings raises ValidationError
    monkeypatch.delenv("NEO4J_URI", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    
    assert "missing" in str(exc_info.value).lower()
