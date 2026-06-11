from __future__ import annotations
from functools import lru_cache
from .base import LLMProvider
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from ..config import settings

_REGISTRY: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider,
}


@lru_cache
def _provider(name: str) -> LLMProvider:
    name = name.lower()
    if name not in _REGISTRY:
        raise ValueError(f"unknown provider: {name}")
    return _REGISTRY[name]()


def drafter() -> LLMProvider:
    return _provider(settings.drafter_provider)


def critic() -> LLMProvider:
    return _provider(settings.critic_provider)
