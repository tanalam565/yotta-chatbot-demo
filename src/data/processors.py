# src/data/processors.py

from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List
from langchain.schema import Document

def chunk_documents(
    docs: List[Document],
    chunk_size: int = 1000,     # larger to keep related sentences together
    chunk_overlap: int = 200    # more overlap for FAQs/short policies
) -> List[Document]:
    """
    Larger chunks + overlap help keep short policy lines (e.g., rent due + grace period)
    within the same chunk so the LLM sees both facts together.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " "]
    )
    return splitter.split_documents(docs)
