from src.data.processors import chunk_documents
from src.chatbot.rag_engine import RAGEngine


def test_chunking_and_ingest(tmp_path, monkeypatch):
    # minimal docs
    docs = {"doc1.txt": "Tenant must earn 3x the monthly rent."}
    chunks = chunk_documents(docs, chunk_size=50, chunk_overlap=0)
    assert len(chunks) >= 1


    # use temp index dir
    monkeypatch.setenv("INDEX_DIR", str(tmp_path / "index"))
    engine = RAGEngine()
    engine.ingest(chunks)
    out = engine.qa("What is the income rule?", k=1)
    assert "answer" in out
    assert isinstance(out["sources"], list)