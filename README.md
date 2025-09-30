# yotta-chatbot-demo
RAG-powered chatbot demo for YottaReal property management by Adara Communities
# YottaReal Chatbot Demo (OpenRouter + DeepSeek :free)

A fully free RAG demo:
- LLM via **OpenRouter** using DeepSeek `:free` models
- Embeddings via **sentence-transformers** (local)
- Vector search via **FAISS**
- FastAPI backend + minimal web UI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Put your OPENROUTER_API_KEY=... in .env
