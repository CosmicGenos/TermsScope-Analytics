"""Anthropic Claude LLM provider with structured output support."""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.config import get_settings
from app.llm.base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider using the official SDK."""

    provider_name = "claude"

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        settings = get_settings()
        self._api_key = settings.anthropic_api_key

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    def _get_client(self):
        """Lazy import to avoid errors when key isn't configured."""
        import anthropic

        return anthropic.AsyncAnthropic(api_key=self._api_key)

    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """Generate structured output using Claude's tool-use pattern.

        Claude doesn't have native JSON mode, so we use a single-tool
        pattern where the tool's input schema IS the Pydantic model.
        """
        client = self._get_client()

        # Build the tool definition from the Pydantic schema
        tool_schema = output_schema.model_json_schema()
        tool = {
            "name": "provide_analysis",
            "description": "Provide the structured analysis result.",
            "input_schema": tool_schema,
        }

        messages = [{"role": "user", "content": prompt}]

        logger.debug(
            "Claude structured generation: model=%s schema=%s",
            self.model,
            output_schema.__name__,
        )

        response = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt or "",
            messages=messages,
            tools=[tool],
            tool_choice={"type": "tool", "name": "provide_analysis"},
            temperature=temperature,
        )

        # Extract the tool input from the response
        for block in response.content:
            if block.type == "tool_use":
                return output_schema.model_validate(block.input)

        raise ValueError("Claude did not return a tool_use block")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a plain-text response."""
        client = self._get_client()

        response = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )

        return response.content[0].text if response.content else ""
