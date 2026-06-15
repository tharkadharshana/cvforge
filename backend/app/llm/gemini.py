from __future__ import annotations
from .base import LLMProvider, call_with_key_rotation
from ..config import settings


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        self._clients: dict[str, object] = {}

    def _client_for(self, key: str):
        client = self._clients.get(key)
        if client is None:
            from google import genai
            from google.genai import types
            client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(timeout=int(settings.llm_timeout_s * 1000)),
            )
            self._clients[key] = client
        return client

    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        from google.genai import types
        model = settings.gemini_model_pro if pro else settings.gemini_model
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.4,
            max_output_tokens=settings.llm_max_tokens,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        def attempt(key: str) -> tuple[str, dict]:
            resp = self._client_for(key).models.generate_content(model=model, contents=user, config=cfg)
            usage = {}
            um = getattr(resp, "usage_metadata", None)
            if um is not None:
                usage = {
                    "prompt_tokens": getattr(um, "prompt_token_count", None),
                    "completion_tokens": getattr(um, "candidates_token_count", None),
                }
            return resp.text, usage

        return call_with_key_rotation(self.name, settings.gemini_api_keys_list, attempt)
