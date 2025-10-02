
---

# 8) Basic test

## `tests/test_chatbot.py`
```python
from src.chatbot.rag_engine import RAGEngine

def test_rag_basic():
    engine = RAGEngine()
    resp = engine.qa_with_history("test-session", "What is the leasing policy?")
    assert "citations" in resp
    assert isinstance(resp["citations"], list)
    assert isinstance(resp["answer"], str)
