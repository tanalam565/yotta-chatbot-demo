import os
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np
from pathlib import Path


try:
    import faiss
except ImportError as e:
    raise RuntimeError("faiss-cpu is required. pip install faiss-cpu")


class LocalFAISS:
    def __init__(self, index_dir: str, embed_model: str):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.model = SentenceTransformer(embed_model)
        self.index_path = self.index_dir / "index.faiss"
        self.meta_path = self.index_dir / "meta.npy"
        self.text_path = self.index_dir / "texts.npy"
        self.index = None
        self.metas: List[Dict] = []
        self.texts: List[str] = []


    def _embed(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, batch_size=32, convert_to_numpy=True, normalize_embeddings=True)


    def build(self, chunks: List[Dict]):
        self.texts = [c["page_content"] for c in chunks]
        self.metas = [c["metadata"] for c in chunks]
        vecs = self._embed(self.texts)
        self.index = faiss.IndexFlatIP(vecs.shape[1]) # cosine via normalized vectors
        self.index.add(vecs)
        self._persist()


    def _persist(self):
        if self.index is None:
            return
        faiss.write_index(self.index, str(self.index_path))
        np.save(self.meta_path, self.metas, allow_pickle=True)
        np.save(self.text_path, self.texts, allow_pickle=True)


    def load(self):
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.metas = list(np.load(self.meta_path, allow_pickle=True))
            self.texts = list(np.load(self.text_path, allow_pickle=True))
        else:
            raise FileNotFoundError("FAISS index not found. Run ingestion first.")


    def search(self, query: str, k: int = 4):
        if self.index is None:
            self.load()
        q_vec = self._embed([query])
        scores, idxs = self.index.search(q_vec, k)
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx == -1:
                continue
            results.append({
                "text": self.texts[idx],
                "metadata": self.metas[idx],
                "score": float(score)
            })
        return results