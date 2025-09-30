from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
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

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> "Settings":
    return Settings()
