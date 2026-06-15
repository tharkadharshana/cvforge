from __future__ import annotations
import httpx
from .base import LLMProvider, call_with_key_rotation
from ..config import settings


class DeepSeekProvider(LLMProvider):
    name = "deepseek"

    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        model = settings.deepseek_model_pro if pro else settings.deepseek_model
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "max_tokens": settings.llm_max_tokens,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        def attempt(key: str) -> tuple[str, dict]:
            with httpx.Client(timeout=settings.llm_timeout_s) as client:
                r = client.post(
                    f"{settings.deepseek_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json=body,
                )
                r.raise_for_status()
                data = r.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {}) or {}
            return text, {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            }

        return call_with_key_rotation(self.name, settings.deepseek_api_keys_list, attempt)
