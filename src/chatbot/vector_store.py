from typing import List, Tuple
from config.settings import get_settings
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

settings = get_settings()

class VectorStore:
    def __init__(self):
        self.emb = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        self.db = None  # FAISS index

    def build(self, texts: List[str], metadatas: List[dict]):
        self.db = FAISS.from_texts(texts=texts, embedding=self.emb, metadatas=metadatas)

    def add(self, texts: List[str], metadatas: List[dict]):
        if self.db is None:
            self.build(texts, metadatas)
        else:
            self.db.add_texts(texts=texts, metadatas=metadatas)

    def search(self, query: str, k: int) -> List[Tuple[str, dict]]:
        if not self.db:
            return []
        docs = self.db.similarity_search(query, k=k)
        return [(d.page_content, d.metadata) for d in docs]
