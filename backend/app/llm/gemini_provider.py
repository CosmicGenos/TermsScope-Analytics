"""Google Gemini LLM provider with structured output support."""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from app.config import get_settings
from app.llm.base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using the google-generativeai SDK."""

    provider_name = "gemini"

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        settings = get_settings()
        self._api_key = settings.google_api_key

    @property
    def default_model(self) -> str:
        return "gemini-2.0-flash"

    def _get_client(self):
        """Lazy import to avoid import errors when key isn't configured."""
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        return genai.GenerativeModel(self.model)

    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """Generate structured output using Gemini's JSON mode."""
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(
            self.model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=output_schema,
                temperature=temperature,
            ),
        )

        logger.debug("Gemini structured generation: model=%s schema=%s", self.model, output_schema.__name__)
        response = await model.generate_content_async(prompt)
        parsed_json = json.loads(response.text)
        return output_schema.model_validate(parsed_json)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a plain-text response."""
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(
            self.model,
            system_instruction=system_prompt,
            generation_config=genai.GenerationConfig(temperature=temperature),
        )

        response = await model.generate_content_async(prompt)
        return response.text or ""
