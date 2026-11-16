import pytest
from ara.llm import get_llm, structured
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


class DummyChatOpenAI:
    """Mock ChatOpenAI that records arguments."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def with_structured_output(self, schema):
        return DummyRunnable(schema)


class DummyRunnable:
    """Simple object that mimics a LangChain Runnable."""

    def __init__(self, schema):
        self.schema = schema

    def run(self, *args, **kwargs):
        return {}


def test_get_llm_reason(monkeypatch):
    dummy = DummyChatOpenAI()
    monkeypatch.setattr("ara.llm.ChatOpenAI", lambda **kw: dummy)
    llm = get_llm("reason")
    assert isinstance(llm, DummyChatOpenAI)
    assert llm.kwargs["model"] == "gpt-4o"
    assert llm.kwargs["temperature"] == 0
    assert llm.kwargs["max_tokens"] == 2000
    assert llm.kwargs["max_retries"] == 3


def test_get_llm_fast(monkeypatch):
    dummy = DummyChatOpenAI()
    monkeypatch.setattr("ara.llm.ChatOpenAI", lambda **kw: dummy)
    llm = get_llm("fast")
    assert isinstance(llm, DummyChatOpenAI)
    assert llm.kwargs["model"] == "gpt-4o-mini"


def test_structured_returns_runnable(monkeypatch):
    dummy_llm = DummyChatOpenAI()
    dummy_runnable = DummyRunnable(schema=object)  # schema type irrelevant for test
    # Patch the method that adds structured_output
    monkeypatch.setattr(
        "ara.llm.ChatOpenAI.with_structured_output",
        lambda self, schema: dummy_runnable,
    )
    llm = get_llm("reason")
    runnable = structured(llm, object)  # schema type does not matter here
    assert hasattr(runnable, "run")
    result = runnable.run()
    assert isinstance(result, dict)
