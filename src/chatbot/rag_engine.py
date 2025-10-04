# src/chatbot/rag_engine.py

from typing import Dict, List, Tuple
import re
import os

from langchain.prompts import ChatPromptTemplate
from langchain.schema import Document

from config.settings import settings
from src.chatbot.llm_handler import get_llm
from src.data.loaders import load_documents
from src.data.processors import chunk_documents
from src.chatbot.vector_store import VectorStore

# -------------------------
# In-memory chat history & session indexes
# -------------------------
_SESSION_MEMORY: Dict[str, List[Dict[str, str]]] = {}
_SESSION_INDEXES: Dict[str, VectorStore] = {}

def _format_history(messages: List[Dict[str, str]]) -> str:
    return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])

# -------------------------
# Prompts
# -------------------------
SYSTEM_PROMPT_PROPERTY = """You are Yotta, a helpful assistant for YottaReal.

CRITICAL INSTRUCTIONS:
- You have been provided with specific document content in the context below.
- Use ONLY the information from the provided context to answer questions.
- The context contains the actual text extracted from the documents provided including uploaded documents by the user.
- If the context contains relevant information, provide a complete answer based on that information.
- Only say "I don't know based on the available documents" if the context truly has NO information related to the question.
- Do NOT say you cannot access files - the file content has already been extracted and provided to you in the context.
- Provide clear, detailed answers using the context information.
- Do NOT include a "Citations" section; citations are added automatically.
- Respond in plain sentences or paragraphs or bullet points without Markdown formatting.
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
- Respond in plain sentences, paragraphs, or bullet points. Do NOT use Markdowns or special formattings.
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
    """Remove leading punctuation, code fences, 'Sources:' lines, and Markdown formatting."""
    raw = (text or "").strip()

    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()

    cleaned = raw.lstrip(":").lstrip().lstrip("-").lstrip("—").strip()
    cleaned = re.sub(r"(?im)^\s*source[s]?\s*:\s*.*$", "", cleaned)
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = re.sub(r"_+", "", cleaned)
    cleaned = re.sub(r"`+", "", cleaned)
    cleaned = cleaned.strip()

    if not cleaned or cleaned in {".", ":", "-", "—"}:
        return "I don't know based on the available documents."
    return cleaned

def _select_citations(answer_text: str, retrieved_docs: List[Document]) -> List[Dict]:
    ans = (answer_text or "").lower()
    numbers = set(re.findall(r'\b\d+\b', ans))
    key_terms = {"grace", "period", "rent", "due", "fee", "policy", "maintenance", "lease", "leasing", "payment",
                 "adar", "adara", "resident", "tenant", "community", "experience", "skills", "education", 
                 "work", "resume", "background", "developer", "engineer", "manager", "sales"}

    selected, seen = [], set()
    for d in retrieved_docs:
        text = (d.page_content or "").lower()
        overlap = sum(1 for n in numbers if n in text) + sum(1 for k in key_terms if k in text)
        if overlap >= 1:  # Lowered threshold
            src = d.metadata.get("source") or d.metadata.get("path") or "document"
            if src not in seen:
                selected.append(src)
                seen.add(src)

    if not selected and retrieved_docs:
        selected = [retrieved_docs[0].metadata.get("source") or "document"]

    return [{"id": i + 1, "source": s} for i, s in enumerate(selected)]

# -------------------------
# Retrieval helpers
# -------------------------
def _keyword_boost(query: str, ranked: List[Tuple[Document, float, int]]) -> List[Tuple[Document, float, int]]:
    q_tokens = set(re.findall(r'\b(?:\d+|\w{3,})\b', (query or "").lower()))
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
        
        # Permanent knowledge base
        self.permanent_store = VectorStore()
        docs = load_documents(settings.docs_dir)
        chunks = chunk_documents(docs)
        self.permanent_db = self.permanent_store.build_or_load(chunks)

    def build_session_index(self, session_id: str, session_dir: str):
        """Build a temporary index for session-specific uploads."""
        if not os.path.exists(session_dir) or not os.listdir(session_dir):
            return
        
        session_store = VectorStore(index_dir=f"data/indexes/session_{session_id}")
        docs = load_documents(session_dir)
        chunks = chunk_documents(docs)
        session_store.build_or_load(chunks)
        _SESSION_INDEXES[session_id] = session_store

    def clear_session_index(self, session_id: str):
        """Remove session-specific index from memory."""
        if session_id in _SESSION_INDEXES:
            del _SESSION_INDEXES[session_id]

    def _retrieve(self, session_id: str, query: str) -> List[Document]:
        """Retrieve from both permanent and session-specific indexes, prioritizing session uploads."""
        k = max(settings.top_k, 4)
        all_docs = []

        # Search session-specific uploads FIRST if they exist
        if session_id in _SESSION_INDEXES:
            try:
                session_db = _SESSION_INDEXES[session_id]._db
                sess_docs = session_db.similarity_search_with_score(query, k=k)
                # Prioritize session docs by giving them better scores (boost them)
                all_docs.extend([(d, s * 0.5, i) for i, (d, s) in enumerate(sess_docs)])
            except Exception as e:
                print(f"Session index search failed: {e}")

        # Then search permanent knowledge base
        try:
            perm_docs = self.permanent_db.similarity_search_with_score(query, k=k)
            all_docs.extend([(d, s, i + 100) for i, (d, s) in enumerate(perm_docs)])
        except Exception as e:
            print(f"Permanent index search failed: {e}")

        if not all_docs:
            return []

        # Sort by similarity score (lower is better for FAISS)
        # Session docs will rank higher due to the 0.5 multiplier
        all_docs.sort(key=lambda x: x[1])
        all_docs = _keyword_boost(query, all_docs)

        return [d for d, _s, _i in all_docs[:max(settings.top_k, 4)]]

    def qa_with_history(self, session_id: str, query: str) -> Dict:
        history = _SESSION_MEMORY.setdefault(session_id, [])

        if "previous question" in (query or "").lower():
            last_q = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
            ans = f'The previous question you asked was: "{last_q}"' if last_q else "No previous question found."
            return {"answer": ans, "citations": []}

        # Search both permanent and session documents
        retrieved = self._retrieve(session_id, query)
        
        if retrieved:
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
            history_text = _format_history(history)
            chain = QA_PROMPT_GENERAL | self.llm
            response = chain.invoke({"history": history_text, "question": query})
            answer_text = _clean_answer(getattr(response, "content", ""))

            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": answer_text})

            return {"answer": answer_text, "citations": []}