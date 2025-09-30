from typing import List, Tuple

def chunk_text(text: str, size: int = 1200, overlap: int = 200) -> List[str]:
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        start = max(0, end - overlap)
        if start == end:
            break
    return chunks

def prepare_corpus(pairs: List[Tuple[str, dict]], size: int, overlap: int):
    texts, metas = [], []
    for text, meta in pairs:
        for ch in chunk_text(text, size, overlap):
            texts.append(ch)
            metas.append(meta)
    return texts, metas
