from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from src.api.routes import router, register_handlers
import os


app = FastAPI(title="YottaReal Chatbot Demo", version="1.0")

# Register error handlers
register_handlers(app)

# CORS (allow local dev / Codespaces)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router FIRST (before static files)
app.include_router(router)

# Serve frontend - MUST BE LAST (catches all remaining routes)
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)