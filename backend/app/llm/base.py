from __future__ import annotations
import json
import time
from abc import ABC, abstractmethod
from ..logging_config import get_logger

log = get_logger("llm")

# Substrings that indicate a transient, retryable provider error (overload /
# rate limiting), as opposed to a permanent failure (bad request, auth, etc).
_RETRYABLE_MARKERS = ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded", "rate limit")
_MAX_RETRIES = 2
_RETRY_BASE_DELAY_S = 1.5


def is_retryable(e: Exception) -> bool:
    s = str(e)
    return any(m.lower() in s.lower() for m in _RETRYABLE_MARKERS)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        """Return (text, usage_dict). usage keys: prompt_tokens, completion_tokens (best effort)."""
        ...

    def complete(self, system: str, user: str, json_mode: bool = False, pro: bool = False) -> str:
        model_tier = "pro" if pro else "std"
        log.info("%s call start tier=%s json=%s sys_chars=%d user_chars=%d",
                 self.name, model_tier, json_mode, len(system), len(user))
        for attempt in range(_MAX_RETRIES + 1):
            t0 = time.perf_counter()
            try:
                text, usage = self._call(system, user, json_mode, pro)
            except Exception as e:
                dt = (time.perf_counter() - t0) * 1000
                if is_retryable(e) and attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY_S * (2 ** attempt)
                    log.warning("%s call failed (retryable) tier=%s attempt=%d/%d after %.0fms: %s -- retrying in %.1fs",
                                 self.name, model_tier, attempt + 1, _MAX_RETRIES + 1, dt, e, delay)
                    time.sleep(delay)
                    continue
                log.error("%s call FAILED tier=%s after %.0fms: %s", self.name, model_tier, dt, e, exc_info=True)
                raise
            break
        dt = (time.perf_counter() - t0) * 1000
        log.info("%s call ok tier=%s %.0fms resp_chars=%d tokens_in=%s tokens_out=%s",
                 self.name, model_tier, dt, len(text or ""),
                 usage.get("prompt_tokens", "?"), usage.get("completion_tokens", "?"))
        log.debug("%s response preview: %s", self.name, (text or "")[:300].replace("\n", " "))
        return text

    def complete_json(self, system: str, user: str, pro: bool = False) -> dict:
        raw = self.complete(system, user, json_mode=True, pro=pro)
        try:
            return _safe_json(raw)
        except ValueError as e:
            log.error("%s JSON parse failed: %s", self.name, e)
            raise


def _safe_json(raw: str) -> dict:
    s = (raw or "").strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
    s = s.strip().strip("`").strip()
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}\n---\n{(raw or '')[:800]}")
