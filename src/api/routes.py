from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.chatbot.rag_engine import RAGEngine
from src.data.loaders import load_documents
from src.data.processors import chunk_documents
from config.settings import settings

router = APIRouter(prefix="/api")
engine = RAGEngine()

class ChatRequest(BaseModel):
    message: str
    top_k: int | None = None

@router.post("/ingest")
def ingest():
    pairs = load_documents(settings.docs_dir)
    if not pairs:
        raise HTTPException(status_code=400, detail="No documents found in data/sample_documents")
    docs = {p: t for p, t in pairs}
    chunks = chunk_documents(docs)
    engine.ingest(chunks)
    return {"status": "ok", "chunks": len(chunks)}

@router.post("/chat")
def chat(req: ChatRequest, request: Request):
    history = request.session.get("history", [])
    history.append({"role": "user", "content": req.message})
    try:
        result = engine.qa_with_history(history, k=req.top_k)
        history.append({"role": "assistant", "content": result["answer"]})
        request.session["history"] = history
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Index not found. Run /api/ingest first.")
