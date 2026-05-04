"""Thin wrapper around the existing Anthropic provider, tuned for judge calls.

The judge uses the same `anthropic.AsyncAnthropic` client as the rest of the
codebase but with much higher max_tokens (Pass-1 outputs can be large) and a
forced temperature of 0 for reproducibility.
"""

from __future__ import annotations

import logging
from typing import Type, TypeVar

from pydantic import BaseModel

from app.config import get_settings
from evals.config import JudgeConfig

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class JudgeClient:
    """Anthropic-backed judge with structured-output support via tool-use."""

    def __init__(self, cfg: JudgeConfig) -> None:
        self.cfg = cfg
        if cfg.judge_provider != "claude":
            raise NotImplementedError(
                f"Only judge_provider='claude' is implemented; got {cfg.judge_provider!r}"
            )
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Configure it in backend/.env before running evals."
            )
        self._api_key = settings.anthropic_api_key

    def _client(self):
        import anthropic
        return anthropic.AsyncAnthropic(api_key=self._api_key)

    async def structured(
        self,
        system: str,
        user: str,
        schema: Type[T],
        *,
        max_tokens: int = 16000,
    ) -> T:
        """Force a structured response by single-tool tool_choice."""
        client = self._client()
        tool_schema = schema.model_json_schema()
        tool = {
            "name": "submit_analysis",
            "description": f"Submit the {schema.__name__} result.",
            "input_schema": tool_schema,
        }
        response = await client.messages.create(
            model=self.cfg.judge_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_analysis"},
            temperature=self.cfg.temperature,
        )
        for block in response.content:
            if block.type == "tool_use":
                return schema.model_validate(block.input)
        raise ValueError(
            f"Judge ({self.cfg.judge_model}) did not return a tool_use block. "
            f"stop_reason={response.stop_reason}"
        )

    async def text(self, system: str, user: str, *, max_tokens: int = 4096) -> str:
        client = self._client()
        response = await client.messages.create(
            model=self.cfg.judge_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=self.cfg.temperature,
        )
        return response.content[0].text if response.content else ""
