from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG"

    # Database
    DATABASE_URL: str

    # LLM
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # LangChain
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: Optional[str] = None
    
    # Vector Store
    # Local ChromaDB is used, no extra config needed.

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
