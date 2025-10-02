from typing import List, Dict
from config.settings import settings
from src.chatbot.vector_store import LocalFAISS
from src.chatbot.llm_handler import generate_answer_with_history
from rapidfuzz import fuzz

MIN_TOP_HIT_SCORE = 0.25   # slightly looser
MIN_HIT_SCORE     = 0.25
MIN_OVERLAP       = 50     # names can be short; lower to 50

def _select_sources(hits: List[Dict], answer: str) -> List[str]:
    if not hits or not answer.strip():
        return []
    strong = [h for h in hits if h.get("score", 0.0) >= MIN_HIT_SCORE]
    if not strong:
        return []
    def overlap(h):
        try: return fuzz.partial_ratio(h.get("text",""), answer)
        except Exception: return 0
    # keep all that meet overlap threshold, dedup by file
    seen, chosen = set(), []
    for h in sorted(strong, key=overlap, reverse=True):
        if overlap(h) < MIN_OVERLAP:
            continue
        src = h.get("metadata", {}).get("source", "unknown")
        if src not in seen:
            seen.add(src)
            chosen.append(src)
    return chosen

class RAGEngine:
    def __init__(self):
        self.store = LocalFAISS(index_dir=settings.index_dir, embed_model=settings.embed_model)

    def ingest(self, chunks: List[Dict]):
        self.store.build(chunks)

    def qa_with_history(self, history: List[Dict[str, str]], k: int | None = None) -> Dict:
        last_user = next((t for t in reversed(history) if t["role"] == "user"), None)
        if not last_user:
            return {"answer": "Please send a message to start.", "sources": [], "hits": []}

        query = last_user["content"]
        k = k or settings.top_k

        # 1) Keyword booster for proper nouns (e.g., 'Brent Bunger')
        kw_hits = self.store.keyword_boost(query)
        hits = kw_hits.copy()

        # 2) Vector search as usual, then merge + unique (prefer keyword hits)
        vec_hits = self.store.search(query, k)
        # merge by source+text identity
        seen = {(h["metadata"].get("source"), h["text"]) for h in hits}
        for h in vec_hits:
            key = (h["metadata"].get("source"), h["text"])
            if key not in seen:
                seen.add(key)
                hits.append(h)

        # 3) Off-topic gate if absolutely nothing meaningful
        if not hits or (not kw_hits and vec_hits and vec_hits[0]["score"] < MIN_TOP_HIT_SCORE):
            return {
                "answer": "I couldn’t find anything about that in the uploaded documents.",
                "sources": [],
                "hits": []
            }

        answer = generate_answer_with_history(history, hits)
        sources = _select_sources(hits, answer)

        if not sources:
            return {
                "answer": "I couldn’t find anything about that in the uploaded documents.",
                "sources": [],
                "hits": hits
            }

        return {"answer": answer, "sources": sources, "hits": hits}
