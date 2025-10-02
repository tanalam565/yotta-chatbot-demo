from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.chatbot.rag_engine import RAGEngine

router = APIRouter(prefix="/api", tags=["chat"])
_engine = RAGEngine()

class ChatRequest(BaseModel):
    message: str
    session_id: str

@router.post("/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    result = _engine.qa_with_history(req.session_id, req.message)
    return result
