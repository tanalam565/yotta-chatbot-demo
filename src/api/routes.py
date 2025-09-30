from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.chatbot.rag_engine import RAGEngine

router = APIRouter()
rag = RAGEngine()

class ChatRequest(BaseModel):
    message: str

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/ingest")
async def ingest():
    count = await rag.ingest_local_folder("data/sample_documents")
    return {"ingested_chunks": count}

@router.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message is empty")
    answer, sources = await rag.answer(req.message)
    return {"answer": answer, "sources": sources}
