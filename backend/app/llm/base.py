"""Abstract base class for all LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Unified interface every LLM provider must implement."""

    provider_name: str = "base"

    def __init__(self, model: str | None = None, **kwargs: Any) -> None:
        self.model = model or self.default_model
        self._extra = kwargs

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier for this provider."""
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_schema: Type[T],
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> T:
        """Generate a structured response matching *output_schema*.

        Parameters
        ----------
        prompt : str
            The user/analysis prompt containing the text to analyze.
        output_schema : Type[T]
            A Pydantic model class. The LLM response **must** conform to this.
        system_prompt : str | None
            Optional system/instruction prompt.
        temperature : float
            Sampling temperature (low = deterministic).

        Returns
        -------
        T
            Parsed Pydantic model instance.
        """
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate a plain-text response (no schema enforcement)."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model}>"
