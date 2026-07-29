from __future__ import annotations
from .base import LLMProvider, call_with_key_rotation
from ..config import settings


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self):
        self._clients: dict[str, object] = {}

    def _client_for(self, key: str):
        client = self._clients.get(key)
        if client is None:
            from openai import OpenAI
            client = OpenAI(api_key=key, timeout=settings.llm_timeout_s)
            self._clients[key] = client
        return client

    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        model = settings.openai_model_pro if pro else settings.openai_model

        def attempt(key: str) -> tuple[str, dict]:
            resp = self._client_for(key).chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.4,
                max_tokens=settings.llm_max_tokens,
                response_format={"type": "json_object"} if json_mode else None,
            )
            usage = {}
            if resp.usage is not None:
                usage = {
                    "prompt_tokens": resp.usage.prompt_tokens,
                    "completion_tokens": resp.usage.completion_tokens,
                }
            return resp.choices[0].message.content, usage

        return call_with_key_rotation(self.name, settings.openai_api_keys_list, attempt)
