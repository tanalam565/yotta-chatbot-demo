import pytest
from src.chatbot.rag_engine import RAGEngine

@pytest.mark.asyncio
async def test_ingest_only():
    rag = RAGEngine()
    n = await rag.ingest_local_folder("data/sample_documents")
    assert n >= 0
