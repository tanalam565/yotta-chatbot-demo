# src/data/loaders.py

import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from typing import List
from langchain.schema import Document

def load_documents(docs_dir: str) -> List[Document]:
    """
    Load .txt and .md files and ensure each Document carries:
      - metadata["source"] = filename (for user-facing citation)
      - metadata["fullpath"] = absolute path (for debugging)
    """
    docs: List[Document] = []
    base = Path(docs_dir)
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}:
            loader = TextLoader(str(p), encoding="utf-8")
            loaded = loader.load()
            for d in loaded:
                d.metadata["source"] = p.name
                d.metadata["fullpath"] = str(p.resolve())
            docs.extend(loaded)
    return docs
