"""LLM factory — supports any OpenAI-compatible API (DeepSeek, Qwen, GLM, etc.)."""

from langchain_openai import ChatOpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE


def create_llm(**overrides: str | float) -> ChatOpenAI:
    """Return a ChatOpenAI instance configured from environment variables.

    Pass keyword args to override individual settings per agent
    (e.g. create_llm(temperature=0.3) for a more deterministic agent).
    """
    return ChatOpenAI(
        model=str(overrides.get("model", LLM_MODEL)),
        api_key=str(overrides.get("api_key", LLM_API_KEY)),
        base_url=str(overrides.get("base_url", LLM_BASE_URL)),
        temperature=float(overrides.get("temperature", LLM_TEMPERATURE)),
        streaming=True,
    )
