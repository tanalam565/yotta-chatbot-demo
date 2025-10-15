# src/chatbot/llm_handler.py

from langchain_openai import ChatOpenAI
from config.settings import settings

def get_llm():
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY not set. Please add it to your .env")

    # Route LangChain's OpenAI client to OpenRouter
    return ChatOpenAI(
        model=settings.openrouter_model,
        temperature=0.3,  # Lower temperature for more consistent responses
        openai_api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",  # Use base_url instead of openai_api_base
        default_headers={
            "HTTP-Referer": "http://localhost:8000",  # Optional but recommended
            "X-Title": "YottaReal Chatbot"  # Optional but recommended
        }
    )