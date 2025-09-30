from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from src.api.routes import router as api_router

settings = get_settings()
app = FastAPI(title="YottaReal Chatbot Demo (OpenRouter + DeepSeek)")

# CORS (open for demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# API routes
app.include_router(api_router, prefix="/api")

# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
