import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from config.settings import settings
from src.api.routes import router


app = FastAPI(title="YottaReal Chatbot Demo")
app.include_router(router)


# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.app_host, port=settings.app_port, reload=True)