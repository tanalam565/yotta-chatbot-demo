from langchain_openai import ChatOpenAI
from config.settings import settings

def get_llm():
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY not set. Please add it to your .env")

    # Route LangChain's OpenAI client to OpenRouter
    return ChatOpenAI(
        model=settings.openrouter_model,
        temperature=0.2,
        openai_api_key=settings.openrouter_api_key,
        openai_api_base="https://openrouter.ai/api/v1",
    )
