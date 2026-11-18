from ara.config import Settings, get_settings


def test_settings_defaults() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.OPENAI_API_KEY is None
    assert settings.NEO4J_URI == "bolt://localhost:7687"
    assert settings.NEO4J_USER == "neo4j"
    assert settings.NEO4J_PASSWORD == ""
    assert settings.VECTOR_DIR == "./vector_store"
    assert settings.ARA_KG_BACKEND == "networkx"
    assert settings.ARA_KG_STORE == "kg_store.json"
    assert settings.LANGCHAIN_TRACING_V2 is True
    assert settings.LANGCHAIN_API_KEY is None
    assert settings.LANGSMITH_PROJECT == "ara-skg"


def test_settings_env_override(monkeypatch) -> None:
    get_settings.cache_clear()
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


def test_settings_defaults_when_env_missing(monkeypatch) -> None:
    """All Settings fields have defaults, so a missing env var never raises."""
    get_settings.cache_clear()
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings()
    assert settings.NEO4J_URI == "bolt://localhost:7687"
    assert settings.ARA_KG_BACKEND == "networkx"
    assert settings.ARA_KG_STORE == "kg_store.json"


def test_settings_kg_backend_override(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ARA_KG_BACKEND", "neo4j")
    monkeypatch.setenv("ARA_KG_STORE", "/tmp/my_kg.json")
    settings = get_settings()
    assert settings.ARA_KG_BACKEND == "neo4j"
    assert settings.ARA_KG_STORE == "/tmp/my_kg.json"
    get_settings.cache_clear()
