from typing import List
from openai import OpenAI
from config.settings import settings


# Configure OpenRouter via OpenAI SDK
client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url="https://openrouter.ai/api/v1",
)


SYSTEM_PROMPT = (
    "You are Yotta, a helpful property management RAG assistant. "
    "Answer using the retrieved context. If unsure, say you don't know and suggest adding documents. "
    "Cite sources by filename when relevant."
)


def generate_answer(query: str, contexts: List[dict]) -> str:
    ctx_blocks = []
    for c in contexts:
        src = c["metadata"].get("source", "unknown")
        ctx_blocks.append(f"[SOURCE: {src}]\n{c['text']}")
    context_str = "\n\n".join(ctx_blocks[:6])

    messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"Question: {query}\n\nContext:\n{context_str}"},
    ]


    resp = client.chat.completions.create(
        model=settings.openrouter_model,
        messages=messages,
        temperature=0.2,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()