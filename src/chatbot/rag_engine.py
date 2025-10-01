from typing import List, Dict
from config.settings import settings
from src.chatbot.vector_store import LocalFAISS
from src.chatbot.llm_handler import generate_answer


class RAGEngine:
    def __init__(self):
        self.store = LocalFAISS(index_dir=settings.index_dir, embed_model=settings.embed_model)


    def ingest(self, chunks: List[Dict]):
        self.store.build(chunks)


    def qa(self, query: str, k: int = None) -> Dict:
        k = k or settings.top_k
        hits = self.store.search(query, k)
        answer = generate_answer(query, hits)
        sources = [h["metadata"].get("source", "unknown") for h in hits]
        return {"answer": answer, "sources": sources, "hits": hits}