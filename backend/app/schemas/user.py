
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """Public user representation."""

    id: UUID
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisHistoryItem(BaseModel):
    """Compact analysis item for the history list."""

    id: UUID
    input_type: str
    input_url: Optional[str] = None
    document_title: Optional[str] = None
    status: str
    overall_score: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
