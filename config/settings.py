## 5) config/settings.py
from pydantic import BaseModel
import os
from dotenv import load_dotenv


load_dotenv()


class Settings(BaseModel):
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "google/gemma-2-9b-it:free")


    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))


    embed_model: str = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    index_dir: str = os.getenv("INDEX_DIR", "storage/index")
    docs_dir: str = os.getenv("DOCS_DIR", "data/sample_documents")
    top_k: int = int(os.getenv("TOP_K", "4"))


settings = Settings()