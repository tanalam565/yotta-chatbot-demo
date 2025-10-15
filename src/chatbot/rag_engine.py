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
    """Format conversation history for prompt context."""
    return "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in messages])

# -------------------------
# Prompts - Ultra-simplified for free models
# -------------------------
SYSTEM_PROMPT_PROPERTY = """Answer the question using only the information provided."""

QA_PROMPT_PROPERTY = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_PROPERTY),
    ("human", "Information: {context}\n\nQuestion: {question}\n\nAnswer:")
])

SYSTEM_PROMPT_GENERAL = """You are a helpful assistant."""

QA_PROMPT_GENERAL = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT_GENERAL),
    ("human", "{question}")
])

# -------------------------
# Output cleaning & citations
# -------------------------
def _clean_answer(text: str) -> str:
    """Remove leading punctuation, code fences, 'Sources:' lines, and Markdown formatting."""
    raw = (text or "").strip()

    # Remove code fences
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()

    # Clean leading punctuation
    cleaned = raw.lstrip(":").lstrip().lstrip("-").lstrip("—").strip()
    
    # Remove "Sources:" lines
    cleaned = re.sub(r"(?im)^\s*source[s]?\s*:\s*.*$", "", cleaned)
    
    # Remove Markdown formatting
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = re.sub(r"_+", "", cleaned)
    cleaned = re.sub(r"`+", "", cleaned)
    cleaned = cleaned.strip()

    # Handle empty responses
    if not cleaned or cleaned in {".", ":", "-", "—"}:
        return "I don't know based on the available documents."
    
    return cleaned

def _select_citations(answer_text: str, retrieved_docs: List[Document]) -> List[Dict]:
    """
    Select relevant citations based on content overlap between answer and retrieved docs.
    
    Args:
        answer_text: The generated answer text
        retrieved_docs: List of retrieved documents
        
    Returns:
        List of citation dictionaries with id and source
    """
    if not retrieved_docs:
        return []
    
    ans = (answer_text or "").lower()
    numbers = set(re.findall(r'\b\d+\b', ans))
    
    # Key terms that indicate relevance
    key_terms = {
        "grace", "period", "rent", "due", "fee", "policy", "maintenance", "lease", 
        "leasing", "payment", "adara", "adar", "resident", "tenant", "community", 
        "experience", "skills", "education", "work", "resume", "background", 
        "developer", "engineer", "manager", "sales", "executive", "president", 
        "vice", "email", "contact", "team", "staff"
    }

    selected, seen = [], set()
    
    for d in retrieved_docs:
        text = (d.page_content or "").lower()
        
        # Calculate overlap score
        overlap = sum(1 for n in numbers if n in text) + sum(1 for k in key_terms if k in text)
        
        if overlap >= 1:
            src = d.metadata.get("source") or d.metadata.get("path") or "document"
            if src not in seen:
                selected.append(src)
                seen.add(src)

    # If no matches found, include the top document
    if not selected and retrieved_docs:
        selected = [retrieved_docs[0].metadata.get("source") or "document"]

    return [{"id": i + 1, "source": s} for i, s in enumerate(selected)]

# -------------------------
# Retrieval helpers
# -------------------------
def _keyword_boost(query: str, ranked: List[Tuple[Document, float, int]]) -> List[Tuple[Document, float, int]]:
    """
    Boost documents that have keyword overlap with the query.
    
    Args:
        query: The user's query
        ranked: List of (Document, score, index) tuples
        
    Returns:
        Re-ranked list of documents
    """
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
    """
    Retrieval-Augmented Generation engine that handles:
    - Permanent knowledge base (from data/sample_documents)
    - Session-specific uploads (temporary, per-user)
    - Chat history management
    - Context-aware question answering
    """
    
    def __init__(self):
        """Initialize the RAG engine with permanent knowledge base."""
        self.llm = get_llm()
        
        # Permanent knowledge base
        self.permanent_store = VectorStore()
        docs = load_documents(settings.docs_dir)
        chunks = chunk_documents(docs)
        self.permanent_db = self.permanent_store.build_or_load(chunks)

    def build_session_index(self, session_id: str, session_dir: str):
        """
        Build a temporary index for session-specific uploads.
        
        Args:
            session_id: Unique session identifier
            session_dir: Directory containing uploaded files for this session
        """
        if not os.path.exists(session_dir) or not os.listdir(session_dir):
            print(f"[RAGEngine] No files in session directory: {session_dir}")
            return
        
        print(f"[RAGEngine] Building session index for: {session_id}")
        session_store = VectorStore(index_dir=f"data/indexes/session_{session_id}")
        docs = load_documents(session_dir)
        chunks = chunk_documents(docs)
        session_store.build_or_load(chunks)
        _SESSION_INDEXES[session_id] = session_store
        print(f"[RAGEngine] Session index built with {len(chunks)} chunks")

    def clear_session_index(self, session_id: str):
        """
        Remove session-specific index from memory.
        
        Args:
            session_id: Session identifier to clear
        """
        if session_id in _SESSION_INDEXES:
            del _SESSION_INDEXES[session_id]
            print(f"[RAGEngine] Cleared session index: {session_id}")

    def _retrieve(self, session_id: str, query: str) -> List[Document]:
        """
        Retrieve documents from both permanent and session-specific indexes.
        Session uploads are prioritized over permanent knowledge base.
        
        Args:
            session_id: Session identifier
            query: User's query
            
        Returns:
            List of relevant documents
        """
        k = max(settings.top_k, 4)
        all_docs = []

        # Search session-specific uploads FIRST if they exist
        if session_id in _SESSION_INDEXES:
            try:
                session_db = _SESSION_INDEXES[session_id]._db
                sess_docs = session_db.similarity_search_with_score(query, k=k)
                # Prioritize session docs by giving them better scores (boost them)
                all_docs.extend([(d, s * 0.5, i) for i, (d, s) in enumerate(sess_docs)])
                print(f"[RAGEngine] Retrieved {len(sess_docs)} docs from session index")
            except Exception as e:
                print(f"[RAGEngine] Session index search failed: {e}")

        # Then search permanent knowledge base
        try:
            perm_docs = self.permanent_db.similarity_search_with_score(query, k=k)
            all_docs.extend([(d, s, i + 100) for i, (d, s) in enumerate(perm_docs)])
            print(f"[RAGEngine] Retrieved {len(perm_docs)} docs from permanent index")
        except Exception as e:
            print(f"[RAGEngine] Permanent index search failed: {e}")

        if not all_docs:
            print("[RAGEngine] No documents retrieved")
            return []

        # Sort by similarity score (lower is better for FAISS)
        # Session docs will rank higher due to the 0.5 multiplier
        all_docs.sort(key=lambda x: x[1])
        all_docs = _keyword_boost(query, all_docs)

        final_docs = [d for d, _s, _i in all_docs[:max(settings.top_k, 4)]]
        print(f"[RAGEngine] Returning {len(final_docs)} documents after ranking")
        return final_docs

    def qa_with_history(self, session_id: str, query: str) -> Dict:
        """
        Answer a question using RAG with conversation history.
        
        Args:
            session_id: Session identifier for history tracking
            query: User's question
            
        Returns:
            Dictionary with 'answer' and 'citations' keys
        """
        history = _SESSION_MEMORY.setdefault(session_id, [])

        # Handle "previous question" queries
        if "previous question" in (query or "").lower():
            last_q = next((m["content"] for m in reversed(history) if m["role"] == "user"), None)
            ans = f'The previous question you asked was: "{last_q}"' if last_q else "No previous question found."
            return {"answer": ans, "citations": []}

        # Search both permanent and session documents
        retrieved = self._retrieve(session_id, query)
        
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Retrieved {len(retrieved)} documents")
        
        # Preview retrieved documents
        for i, doc in enumerate(retrieved[:2], 1):
            preview = doc.page_content[:200].replace('\n', ' ')
            print(f"\nDoc {i} preview:\n{preview}")
            print(f"Source: {doc.metadata.get('source', 'unknown')}")
        print(f"{'='*60}\n")
        
        if retrieved:
            # Build context from retrieved documents - LIMIT to top 2 for free models
            top_docs = retrieved[:2]  # Only use top 2 most relevant docs
            context_block = "\n\n".join([d.page_content for d in top_docs])
            
            # Truncate context if too long (free models struggle with long context)
            max_context_length = 1500  # characters
            if len(context_block) > max_context_length:
                context_block = context_block[:max_context_length] + "..."

            # Generate answer using context (no history to avoid confusion)
            chain = QA_PROMPT_PROPERTY | self.llm
            response = chain.invoke({
                "question": query, 
                "context": context_block
            })
            answer_text = _clean_answer(getattr(response, "content", ""))
            
            print(f"DEBUG - Context length: {len(context_block)} chars")
            print(f"DEBUG - Raw LLM response (first 200 chars): {getattr(response, 'content', '')[:200]}")
            print(f"DEBUG - Cleaned answer (first 200 chars): {answer_text[:200]}")

            # Update history
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": answer_text})

            # FIXED: Use 'retrieved' instead of 'retrieved_docs'
            citations = _select_citations(answer_text, retrieved)
            return {"answer": answer_text, "citations": citations}
        else:
            # No relevant documents found - use general knowledge
            chain = QA_PROMPT_GENERAL | self.llm
            response = chain.invoke({"question": query})
            answer_text = _clean_answer(getattr(response, "content", ""))

            # Update history
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": answer_text})

            return {"answer": answer_text, "citations": []}