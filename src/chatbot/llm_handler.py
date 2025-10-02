# src/chatbot/llm_handler.py
from typing import List, Dict
from openai import OpenAI
from config.settings import settings

client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)

SYSTEM_PROMPT = (
    "You are Yotta, a property-management RAG assistant for Adara/YottaReal.\n"
    "Follow the rules strictly:\n"
    "1) ONLY answer if the answer is supported by the retrieved context.\n"
    "2) If context is empty or irrelevant, reply exactly: "
    "'I couldn’t find anything about that in the uploaded documents.'\n"
    "3) Be concise, texting tone; do not include sources in your text (UI will show citations).\n"
)

def _build_context_block(contexts: List[dict]) -> str:
    blocks = []
    for c in contexts[:8]:
        src = c.get("metadata", {}).get("source", "unknown")
        text = c.get("text", "")
        blocks.append(f"[SOURCE: {src}]\n{text}")
    return "\n\n".join(blocks)

def generate_answer_with_history(history: List[Dict[str, str]], contexts: List[dict]) -> str:
    context_block = _build_context_block(contexts)

    # Compose messages: system + (optional) context + conversation turns
    messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context_block.strip():
        # Add context as assistant-visible guidance
        messages.append({"role": "system", "content": f"Retrieved context:\n{context_block}"})
    # Keep last ~10 turns
    turns = history[-10:] if len(history) > 10 else history
    messages.extend(turns)

    resp = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        temperature=0.0,   # deterministic, reduces drift
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()
