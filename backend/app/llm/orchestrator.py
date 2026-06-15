from __future__ import annotations
from functools import lru_cache
from .base import LLMProvider
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from ..config import settings
from ..logging_config import get_logger

log = get_logger("llm")

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


class _FallbackProvider:
    """Tries `primary` first; on failure (after primary's own retries are
    exhausted) retries the same request against `fallback`."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self.primary = primary
        self.fallback = fallback
        self.name = f"{primary.name}(fallback={fallback.name})"

    def complete(self, system: str, user: str, json_mode: bool = False, pro: bool = False) -> str:
        try:
            return self.primary.complete(system, user, json_mode, pro)
        except Exception as e:
            log.warning("%s failed, falling back to %s: %s", self.primary.name, self.fallback.name, e)
            return self.fallback.complete(system, user, json_mode, pro)

    def complete_json(self, system: str, user: str, pro: bool = False) -> dict:
        try:
            return self.primary.complete_json(system, user, pro)
        except Exception as e:
            log.warning("%s failed, falling back to %s: %s", self.primary.name, self.fallback.name, e)
            return self.fallback.complete_json(system, user, pro)


def _with_fallback(primary_name: str, fallback_name: str) -> LLMProvider:
    primary = _provider(primary_name)
    if not fallback_name or fallback_name.lower() == primary_name.lower():
        return primary
    return _FallbackProvider(primary, _provider(fallback_name))


def drafter() -> LLMProvider:
    return _with_fallback(settings.drafter_provider, settings.drafter_fallback_provider)


def critic() -> LLMProvider:
    return _with_fallback(settings.critic_provider, settings.critic_fallback_provider)
