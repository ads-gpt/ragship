from openai import OpenAI

from app.config import get_settings


def get_llm_client() -> tuple[OpenAI, str]:
    settings = get_settings()

    if settings.llm_provider == "groq":
        if not settings.groq_key:
            raise RuntimeError("GROQ_KEY is required when LLM_PROVIDER=groq.")
        return (
            OpenAI(
                api_key=settings.groq_key,
                base_url=settings.groq_base_url,
            ),
            settings.groq_model,
        )

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")

    return OpenAI(api_key=settings.openai_api_key), settings.openai_model
