from __future__ import annotations
from functools import lru_cache
from .base import LLMProvider
from .deepseek import DeepSeekProvider
from .gemini import GeminiProvider
from .openai_provider import OpenAIProvider
from ..config import settings
from ..logging_config import get_logger

log = get_logger("llm")

_REGISTRY: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


@lru_cache
def _provider(name: str) -> LLMProvider:
    name = name.lower()
    if name not in _REGISTRY:
        raise ValueError(f"unknown provider: {name}")
    return _REGISTRY[name]()


class _ChainProvider:
    """Tries each provider in order; on failure (after that provider's own
    key-rotation retries are exhausted) falls through to the next. Raises the
    last provider's error if every one fails."""

    def __init__(self, providers: list[LLMProvider]):
        self.providers = providers
        self.name = "->".join(p.name for p in providers)

    def _run(self, method: str, *args, **kwargs):
        last_exc: Exception | None = None
        for i, p in enumerate(self.providers):
            try:
                return getattr(p, method)(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i < len(self.providers) - 1:
                    log.warning("%s failed, falling back to %s: %s", p.name, self.providers[i + 1].name, e)
                    continue
                raise
        raise last_exc  # pragma: no cover -- unreachable, providers is never empty

    def complete(self, system: str, user: str, json_mode: bool = False, pro: bool = False) -> str:
        return self._run("complete", system, user, json_mode, pro)

    def complete_json(self, system: str, user: str, pro: bool = False) -> dict:
        return self._run("complete_json", system, user, pro)


def _chain() -> LLMProvider:
    names = [n.strip() for n in settings.llm_provider_chain.split(",") if n.strip()]
    providers = [_provider(n) for n in names]
    return providers[0] if len(providers) == 1 else _ChainProvider(providers)


drafter = critic = _chain
