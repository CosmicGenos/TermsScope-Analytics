"""Input schemas for analysis requests."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class InputType(str, Enum):
    """Supported input types."""

    URL = "url"
    TEXT = "text"
    FILE = "file"


class AnalysisRequest(BaseModel):
    """Request body for starting an analysis."""

    input_type: InputType
    url: Optional[HttpUrl] = Field(None, description="URL to a Terms of Service page")
    text: Optional[str] = Field(None, description="Pasted ToS text", max_length=500_000)
    llm_provider: Optional[str] = Field(None, description="Override LLM provider")
    llm_model: Optional[str] = Field(None, description="Override LLM model")

    def model_post_init(self, __context) -> None:
        """Validate that the correct input field is provided."""
        if self.input_type == InputType.URL and not self.url:
            raise ValueError("URL is required when input_type is 'url'")
        if self.input_type == InputType.TEXT and not self.text:
            raise ValueError("Text is required when input_type is 'text'")


class AnalysisStatusResponse(BaseModel):
    """Short status response for polling."""

    analysis_id: str
    status: str
    progress: int = Field(0, ge=0, le=100)
    message: Optional[str] = None
