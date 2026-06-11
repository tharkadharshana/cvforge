from __future__ import annotations
import httpx
from .base import LLMProvider
from ..config import settings


class DeepSeekProvider(LLMProvider):
    name = "deepseek"

    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        model = settings.deepseek_model_pro if pro else settings.deepseek_model
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.4,
            "max_tokens": 8000,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=180.0) as client:
            r = client.post(
                f"{settings.deepseek_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
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
