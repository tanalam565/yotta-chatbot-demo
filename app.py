# app.py
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware  
from config.settings import settings
from src.api.routes import router

app = FastAPI(title="YottaReal Chatbot Demo")

# add this line (use a better secret in .env for prod)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "dev-secret"))

app.include_router(router)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.app_host, port=settings.app_port, reload=True)
