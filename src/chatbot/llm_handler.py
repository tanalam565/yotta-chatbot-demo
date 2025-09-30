from config.settings import get_settings
from openai import OpenAI

settings = get_settings()

SYSTEM_FALLBACK = (
    "You are Yotta, a helpful assistant for property management (Adara Communities). "
    "Be concise, cite filenames when relevant, and say when you don't know."
)

class LLMHandler:
    def __init__(self):
        if settings.llm_provider != "openrouter":
            raise ValueError("Unsupported LLM provider (expected 'openrouter').")
        # OpenAI-compatible client pointed to OpenRouter
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        self.model = settings.openrouter_model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        # OpenAI SDK is sync; keep it simple here
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": (system_prompt or SYSTEM_FALLBACK)},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
        )
        return resp.choices[0].message.content.strip()
