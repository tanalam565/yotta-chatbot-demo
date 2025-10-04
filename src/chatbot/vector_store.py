# src/chatbot/vector_store.py
import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import settings

class VectorStore:
    def __init__(self, index_dir=None):
        self.index_dir = index_dir or settings.index_dir
        self.embed_model = settings.embed_model
        self._embeddings = HuggingFaceEmbeddings(model_name=self.embed_model)
        self._db = None

    def build_or_load(self, chunks):
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        index_file = os.path.join(self.index_dir, "faiss.index")
        if os.path.exists(index_file):
            self._db = FAISS.load_local(self.index_dir, self._embeddings, allow_dangerous_deserialization=True)
        else:
            self._db = FAISS.from_documents(chunks, self._embeddings)
            self._db.save_local(self.index_dir)
        return self._db
        
    def rebuild(self, chunks):
        """Re-create the FAISS index from the given chunks and write to disk."""
        self._db = FAISS.from_documents(chunks, self._embeddings)
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        self._db.save_local(self.index_dir)

    def as_retriever(self, k: int):
        if not self._db:
            raise RuntimeError("Vector DB not loaded. Call build_or_load first.")
        return self._db.as_retriever(search_kwargs={"k": k})