from config.settings import get_settings
from src.chatbot.vector_store import VectorStore
from src.chatbot.llm_handler import LLMHandler
from src.data.loaders import load_folder
from src.data.processors import prepare_corpus

settings = get_settings()

SYSTEM_PROMPT = """You are Yotta, an assistant for property management (Adara Communities).
Answer concisely with citations to the source filenames (metadata path) when helpful.
If unsure, say you don't know.
"""

class RAGEngine:
    def __init__(self):
        self.vs = VectorStore()
        self.llm = LLMHandler()
        self.ready = False

    async def ingest_local_folder(self, folder: str) -> int:
        pairs = load_folder(folder)
        texts, metas = prepare_corpus(pairs, settings.chunk_size, settings.chunk_overlap)
        if not texts:
            return 0
        self.vs.build(texts, metas)
        self.ready = True
        return len(texts)

    async def answer(self, query: str):
        if not self.ready:
            await self.ingest_local_folder("data/sample_documents")
        retrieved = self.vs.search(query, k=settings.top_k)
        context = "\n\n".join([f"[Source: {m.get('path','N/A')}]\n{t}" for t, m in retrieved]) or "No context."
        prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {query}\n"
            f"Instructions: Prefer grounded answers; if context is weak, say so."
        )
        response = await self.llm.generate(SYSTEM_PROMPT, prompt)
        sources = [m for _, m in retrieved]
        return response, sources
