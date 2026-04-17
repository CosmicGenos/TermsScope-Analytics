"""OpenAI LLM provider with structured output support."""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get_settings
from app.llm.base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider using the official SDK."""

    provider_name = "openai"

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """Generate a structured response using OpenAI's response_format."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug("OpenAI structured generation: model=%s schema=%s", self.model, output_schema.__name__)

        response = await self._client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=output_schema,
            temperature=temperature,
        )

        parsed = response.choices[0].message.parsed
        if parsed is None:
            # Fallback: try manual parsing from content
            content = response.choices[0].message.content or "{}"
            parsed = output_schema.model_validate_json(content)

        return parsed

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a plain-text response."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )

        return response.choices[0].message.content or ""
