"""Chat model that tries Anthropic first and falls back to OpenAI."""

from typing import Any, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from ai_workflow.settings import settings


class ChatWithFallback:
    """Calls the first model; if it raises an error, tries the next one."""

    def __init__(self, models: List[Any]):
        self.models = models

    @staticmethod
    def _first_then_rest(models: List[Any]):
        return models[0].with_fallbacks(models[1:])

    async def ainvoke(self, messages):
        return await self._first_then_rest(self.models).ainvoke(messages)

    def with_structured_output(self, schema):
        return self._first_then_rest([model.with_structured_output(schema) for model in self.models])


def build_llm(temperature: float, max_tokens: int) -> Optional[ChatWithFallback]:
    """Anthropic first, OpenAI second. Each one is used only if its API key is set. None if neither is."""
    models = []
    anthropic_key = settings.ANTHROPIC_API_KEY.get_secret_value()
    if anthropic_key:
        models.append(ChatAnthropic(
            anthropic_api_key=anthropic_key,
            model=settings.ANTHROPIC_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        ))
    openai_key = settings.OPENAI_API_KEY.get_secret_value()
    if openai_key:
        models.append(ChatOpenAI(
            api_key=openai_key,
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=settings.LLM_MAX_RETRIES,
        ))
    return ChatWithFallback(models) if models else None
