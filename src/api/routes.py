from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config.settings import settings
from src.data.loaders import load_documents
from src.data.processors import chunk_documents
from src.chatbot.rag_engine import RAGEngine


router = APIRouter(prefix="/api")
engine = RAGEngine()


class ChatRequest(BaseModel):
    query: str
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
def chat(req: ChatRequest):
    try:
        result = engine.qa(req.query, k=req.top_k)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Index not found. Run /api/ingest first.")