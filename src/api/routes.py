# src/api/routes.py
from fastapi import APIRouter, HTTPException, Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel
from src.chatbot.rag_engine import RAGEngine

router = APIRouter(prefix="/api", tags=["chat"])
_engine = RAGEngine()

# Clean JSON errors so the frontend can show them
def register_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid request body", "errors": exc.errors()},
        )

class ChatRequest(BaseModel):
    message: Optional[str] = None
    session_id: Optional[str] = None

@router.post("/chat")
async def chat(req: Request):
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body must be JSON")

    print("DEBUG /api/chat payload:", data)

    # accept both 'message' and 'question', ignore extras like 'top_k'
    message = (data.get("message") or data.get("question") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Field 'message' (or 'question') is required and must be non-empty")

    session_id = data.get("session_id") or str(uuid4())

    # optional: allow top_k override safely
    try:
        if "top_k" in data:
            settings.top_k = int(data["top_k"]) or settings.top_k
    except Exception:
        pass

    result = _engine.qa_with_history(session_id, message)
    return result

