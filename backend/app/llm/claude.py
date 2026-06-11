from __future__ import annotations
import anthropic
from .base import LLMProvider
from ..config import settings


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _call(self, system: str, user: str, json_mode: bool, pro: bool) -> tuple[str, dict]:
        model = settings.claude_model_pro if pro else settings.claude_model
        max_tokens = 4096 if pro else 2048

        sys_prompt = system
        if json_mode:
            sys_prompt = system + "\n\nRespond with valid JSON only — no markdown fences, no commentary."

        msg = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=sys_prompt,
            messages=[{"role": "user", "content": user}],
        )
        text = msg.content[0].text
        usage = {
            "prompt_tokens": msg.usage.input_tokens,
            "completion_tokens": msg.usage.output_tokens,
        }
        return text, usage
