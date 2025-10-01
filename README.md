# YottaReal Chatbot Demo (Free Stack)


A demo RAG chatbot named **Yotta** for property management scenarios (Adara Communities). Built with free components:


- LLM: OpenRouter (free-tier)
- Embeddings: sentence-transformers (local)
- Vector Store: FAISS (local)
- API: FastAPI
- Frontend: vanilla HTML/CSS/JS


## Quickstart


```bash
git clone <YOUR_REPO_URL>
cd yottareal-chatbot-demo
python -m venv .venv && source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env # then edit OPENROUTER_API_KEY
python app.py # starts FastAPI at http://localhost:8000