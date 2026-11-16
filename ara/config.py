from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    NEO4J_URI: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="", env="NEO4J_PASSWORD")
    VECTOR_DIR: str = Field(default="./vector_store", env="VECTOR_DIR")
    LANGCHAIN_TRACING_V2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    LANGCHAIN_API_KEY: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    LANGSMITH_PROJECT: str = Field(default="ara-skg", env="LANGSMITH_PROJECT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    return Settings()
