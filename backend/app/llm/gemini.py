from __future__ import annotations
from .base import LLMProvider
from ..config import settings


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.gemini_api_key:
                raise RuntimeError("GEMINI_API_KEY not set")
            from google import genai
            from google.genai import types
            self._client = genai.Client(
                api_key=settings.gemini_api_key,
                http_options=types.HttpOptions(timeout=int(settings.llm_timeout_s * 1000)),
            )
        return self._client

    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        from google.genai import types
        client = self._get_client()
        model = settings.gemini_model_pro if pro else settings.gemini_model
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.4,
            max_output_tokens=settings.llm_max_tokens,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        resp = client.models.generate_content(model=model, contents=user, config=cfg)
        usage = {}
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            usage = {
                "prompt_tokens": getattr(um, "prompt_token_count", None),
                "completion_tokens": getattr(um, "candidates_token_count", None),
            }
        return resp.text, usage
