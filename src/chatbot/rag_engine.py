# src/chatbot/rag_engine.py

from typing import Dict, List, Tuple
import re

from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

from config.settings import settings
from src.chatbot.llm_handler import get_llm
from src.data.loaders import load_documents
from src.data.processors import chunk_documents
from src.chatbot.vector_store import VectorStore

# -------------------------
# In-memory chat history
# -------------------------
_SESSION_MEMORY: Dict[str, List[Dict[str, str]]] = {}

def _format_history(messages: List[Dict[str, str]]) -> str:
    return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])

# -------------------------
# Intent detection
# -------------------------
PROPERTY_KEYWORDS = {
    "rent", "lease", "leasing", "payment", "pay", "late", "grace", "maintenance",
    "work order", "repair", "unit", "apartment", "policy", "screening", "pet",
    "deposit", "move-in", "move in", "move-out", "move out", "renewal", "yottareal",
    "adara", "community", "hoa", "notice", "eviction", "fee", "utilities",
    "parking", "amenities", "resident", "tenant", "application"
}

def _is_property_related(query: str) -> bool:
    q = (query or "").lower()
    return any(k in q for k in PROPERTY_KEYWORDS)

# -------------------------
# Prompts
# -------------------------
SYSTEM_PROMPT_PROPERTY = """You are Yotta, a helpful property management assistant for YottaReal (Adara Communities).

RULES:
- Answer ONLY using the provided context from the documents.
- If the answer is not in the context, say: "I don’t know based on the available documents."
- Do NOT include a "Citations" section in your answer; the application will add citations automatically.
- Provide clear, factual, and complete answers (not just one sentence) when details exist in the documents.
"""

QA_PROMPT_PROPERTY = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_PROPERTY),
    ("human",
     "Conversation so far:\n{history}\n\n"
     "User question: {question}\n\n"
     "Relevant context from documents:\n{context}\n\n"
     "Answer ONLY using the context above.")
])

SYSTEM_PROMPT_GENERAL = """You are Yotta, a friendly assistant for YottaReal.
You can answer small-talk and general-knowledge questions directly.
- Be short and clear.
- Do NOT add citations.
- If user asks for your name, say you're Yotta.
"""

QA_PROMPT_GENERAL = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_GENERAL),
    ("human",
     "Conversation so far:\n{history}\n\n"
     "User question: {question}\n\n"
     "Answer directly and concisely (no citations).")
])

# -------------------------
# Output cleaning & citations
# -------------------------
def _clean_answer(text: str) -> str:
    """Remove stray leading punctuation; only fallback if truly empty."""
    raw = (text or "").strip()
    cleaned = raw.lstrip(":").lstrip().lstrip("-").lstrip("—").strip()
    if not cleaned or cleaned in {".", ":", "-", "—"}:
        return "I don’t know based on the available documents."
    return cleaned

def _select_citations(answer_text: str, retrieved_docs: List[Document]) -> List[Dict]:
    """
    Strict selection:
      - Match numeric facts and relevant key phrases contained in the final answer.
      - Require >= 2 overlaps (numbers or key terms) for a doc to count.
      - If nothing matches, fall back to the single top retrieved doc.
    """
    ans = (answer_text or "").lower()
    numbers = set(re.findall(r'\b\d+\b', ans))
    key_terms = {"grace", "period", "rent", "due", "fee", "policy", "maintenance", "lease", "leasing", "payment",
                 "adar", "adara", "resident", "tenant", "community"}

    selected, seen = [], set()
    for d in retrieved_docs:
        text = (d.page_content or "").lower()
        overlap = 0
        overlap += sum(1 for n in numbers if n in text)
        overlap += sum(1 for k in key_terms if k in text)
        if overlap >= 2:
            src = d.metadata.get("source") or d.metadata.get("path") or "document"
            if src not in seen:
                selected.append(src)
                seen.add(src)

    if not selected and retrieved_docs:
        selected = [retrieved_docs[0].metadata.get("source") or "document"]

    return [{"id": i + 1, "source": s} for i, s in enumerate(selected)]

# -------------------------
# Retrieval helpers (FAISS-safe)
# -------------------------
def _keyword_boost(query: str, ranked: List[Tuple[Document, float, int]]) -> List[Tuple[Document, float, int]]:
    q_tokens = set(re.findall(r'\b(?:\d+|\w{4,})\b', (query or "").lower()))
    def boost_index(item):
        d, _score, idx = item
        text = (d.page_content or "").lower()
        has_overlap = any(t in text for t in q_tokens)
        return (idx - 0.5) if has_overlap else idx
    ranked.sort(key=boost_index)
    return ranked

# -------------------------
# RAG Engine
# -------------------------
class RAGEngine:
    def __init__(self):
        self.llm = get_llm()
        self.store = VectorStore()

        docs = load_documents(settings.docs_dir)
        chunks = chunk_documents(docs)  # chunk_size updated in processors.py
        self.db = self.store.build_or_load(chunks)
        self.retriever = self.store.as_retriever(k=settings.top_k)

    def _retrieve(self, query: str) -> List[Document]:
        """
        Use FAISS similarity_search_with_score (no 0–1 relevance assumption).
        Rank by returned order + tiny keyword boost. Keep at most 3–4 chunks for richer answers.
        """
        k = max(settings.top_k, 8)
        try:
            docs_with_scores = self.db.similarity_search_with_score(query, k=k)  # [(Document, score)]
            ranked = [(d, s, i) for i, (d, s) in enumerate(docs_with_scores)]
        except Exception:
            docs = self.retriever.get_relevant_documents(query)
            ranked = [(d, 0.0, i) for i, d in enumerate(docs)]

        ranked = _keyword_boost(query, ranked)
        TOP_CONTEXT = min(settings.top_k, 4)  # allow up to 4 chunks for completeness
        return [d for d, _s, _i in ranked[:TOP_CONTEXT]]

    def qa_with_history(self, session_id: str, query: str) -> Dict:
        history = _SESSION_MEMORY.setdefault(session_id, [])

        # "previous question" shortcut
        if "previous question" in (query or "").lower():
            last_q = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
            ans = f'The previous question you asked was: "{last_q}"' if last_q else "No previous question found."
            return {"answer": ans, "citations": []}

        is_property = _is_property_related(query)

        if is_property:
            # PROPERTY / RAG MODE
            retrieved = self._retrieve(query)
            if not retrieved:
                history.append({"role": "user", "content": query})
                fallback = "I don’t know based on the available documents."
                history.append({"role": "assistant", "content": fallback})
                return {"answer": fallback, "citations": []}

            context_block = "\n\n".join([f"[{i+1}] {d.page_content}" for i, d in enumerate(retrieved)])
            history_text = _format_history(history)

            chain = QA_PROMPT_PROPERTY | self.llm
            response = chain.invoke({"history": history_text, "question": query, "context": context_block})
            answer_text = _clean_answer(getattr(response, "content", ""))

            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": answer_text})

            citations = _select_citations(answer_text, retrieved)
            return {"answer": answer_text, "citations": citations}

        else:
            # GENERAL / SMALL-TALK MODE (no citations)
            history_text = _format_history(history)
            chain = QA_PROMPT_GENERAL | self.llm
            response = chain.invoke({"history": history_text, "question": query})
            answer_text = _clean_answer(getattr(response, "content", ""))

            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": answer_text})

            return {"answer": answer_text, "citations": []}
