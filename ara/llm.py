from typing import Literal, TypeVar, Callable
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def get_llm(tier: Literal["reason", "fast"] = "reason") -> ChatOpenAI:
    """Factory that returns a LangChain LLM instance."""
    if tier == "fast":
        model = "gpt-4o-mini"
    else:
        model = "gpt-4o"
    return ChatOpenAI(model=model, temperature=0, max_tokens=2000)

def structured(llm: ChatOpenAI, schema: type[T]) -> Callable[[BaseMessage], T]:
    """Wrap an LLM with structured output for the given Pydantic schema."""
    return llm.with_structured_output(schema)
