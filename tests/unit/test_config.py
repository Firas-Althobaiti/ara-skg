from ara.config import Settings, get_settings

_ALL_ENV_VARS = (
    "OPENAI_API_KEY",
    "NEO4J_URI",
    "NEO4J_USER",
    "NEO4J_PASSWORD",
    "NCBI_API_KEY",
    "LINKING_MODE",
    "EXTRACTION_MODE",
    "HYPOTHESIS_MODE",
    "EVAL_CACHE",
    "VECTOR_DIR",
    "ARA_KG_BACKEND",
    "ARA_KG_STORE",
    "LANGCHAIN_TRACING_V2",
    "LANGCHAIN_API_KEY",
    "LANGSMITH_PROJECT",
)


def test_settings_defaults(monkeypatch, tmp_path) -> None:
    """Defaults hold with NO env vars and NO .env file.

    chdir to tmp_path so a real ``.env`` in the repo root can never leak
    into this test — it must pass with and without a .env present.
    """
    monkeypatch.chdir(tmp_path)
    for var in _ALL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert isinstance(settings, Settings)
        assert settings.OPENAI_API_KEY is None
        assert settings.NCBI_API_KEY is None
        assert settings.NEO4J_URI == "bolt://localhost:7687"
        assert settings.NEO4J_USER == "neo4j"
        assert settings.NEO4J_PASSWORD == ""
        assert settings.LINKING_MODE == "noop"
        assert settings.EXTRACTION_MODE == "mock"
        assert settings.HYPOTHESIS_MODE == "mock"
        assert settings.EVAL_CACHE is False
        assert settings.VECTOR_DIR == "./vector_store"
        assert settings.ARA_KG_BACKEND == "networkx"
        assert settings.ARA_KG_STORE == "kg_store.json"
        assert settings.LANGCHAIN_TRACING_V2 is True
        assert settings.LANGCHAIN_API_KEY is None
        assert settings.LANGSMITH_PROJECT == "ara-skg"
    finally:
        get_settings.cache_clear()


def test_settings_defaults_with_dotenv_present(monkeypatch, tmp_path) -> None:
    """Simulates a real .env (values set via env vars, as pydantic-settings
    would read them from a .env file) — defaults test above must still be
    the one that owns the no-env case; here we assert override works."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-dotenv")
    monkeypatch.setenv("EXTRACTION_MODE", "live")
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.OPENAI_API_KEY == "sk-from-dotenv"
        assert settings.EXTRACTION_MODE == "live"
        # untouched vars keep defaults
        assert settings.ARA_KG_BACKEND == "networkx"
    finally:
        get_settings.cache_clear()


def test_settings_env_override(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
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
    get_settings.cache_clear()


def test_settings_defaults_when_env_missing(monkeypatch, tmp_path) -> None:
    """All Settings fields have defaults, so a missing env var never raises."""
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    for var in ("NEO4J_URI", "OPENAI_API_KEY", "ARA_KG_BACKEND", "ARA_KG_STORE"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings()
    assert settings.NEO4J_URI == "bolt://localhost:7687"
    assert settings.ARA_KG_BACKEND == "networkx"
    assert settings.ARA_KG_STORE == "kg_store.json"
    get_settings.cache_clear()


def test_settings_kg_backend_override(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    monkeypatch.setenv("ARA_KG_BACKEND", "neo4j")
    monkeypatch.setenv("ARA_KG_STORE", "/tmp/my_kg.json")
    settings = get_settings()
    assert settings.ARA_KG_BACKEND == "neo4j"
    assert settings.ARA_KG_STORE == "/tmp/my_kg.json"
    get_settings.cache_clear()
