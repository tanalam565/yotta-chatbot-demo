from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict  # <-- v2 way

class Settings(BaseSettings):
    # Tell pydantic-settings where to find the .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM over OpenRouter
    llm_provider: str = "openrouter"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-r1:free"

    # Embeddings (local)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Retrieval config
    top_k: int = 4
    chunk_size: int = 1200
    chunk_overlap: int = 200

    log_level: str = "INFO"

@lru_cache
def get_settings() -> "Settings":
    return Settings()
