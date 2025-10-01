from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import Dict, List


def chunk_documents(docs: Dict[str, str], chunk_size: int = 800, chunk_overlap: int = 150) -> List[Dict]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []
    for path, text in docs.items():
        for i, chunk in enumerate(splitter.split_text(text)):
            all_chunks.append({
                "page_content": chunk,
                "metadata": {"source": path, "chunk": i}
            })
    return all_chunks