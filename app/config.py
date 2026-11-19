import os
from functools import lru_cache
from dotenv import load_dotenv

# Pre-load environment variables from .env if present
load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import AliasChoices, Field

    class Settings(BaseSettings):
        """Application settings loaded using pydantic-settings."""

        # Qdrant Cloud Configuration
        QDRANT_URL: str = Field(
            default="",
            description="Qdrant Cloud cluster endpoint URL",
        )
        QDRANT_API_KEY: str = Field(
            default="",
            description="Qdrant Cloud API Key",
        )

        # Gemini LLM Configuration
        GEMINI_API_KEY: str = Field(
            default="",
            validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"),
            description="Gemini API Key for LLM requests",
        )
        GEMINI_MODEL: str = Field(
            default="gemini-1.5-flash",
            description="Gemini model name to use for generation",
        )
        GEMINI_BASE_URL: str = Field(
            default="https://generativelanguage.googleapis.com/v1beta/openai/",
            description="Base URL for Gemini using the OpenAI-compatible endpoint",
        )

        # RAG / Vector DB Configuration
        QDRANT_COLLECTION_NAME: str = Field(
            default="rag_collection",
            description="Qdrant collection name for vector search",
        )
        EMBEDDING_MODEL_NAME: str = Field(
            default="BAAI/bge-small-en-v1.5",
            description="Embedding model name for FastEmbed",
        )

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

except ImportError:
    # Graceful fallback to os.getenv when pydantic-settings is not installed
    class Settings:  # type: ignore[no-redef]
        """Fallback application settings loaded using os.getenv."""

        def __init__(self) -> None:
            self.QDRANT_URL: str = os.getenv("QDRANT_URL", "")
            self.QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
            self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
            self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            self.GEMINI_BASE_URL: str = os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            self.QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "rag_collection")
            self.EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached instance of Settings."""
    return Settings()


# Singleton instance for direct imports
settings = get_settings()
