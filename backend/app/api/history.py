"""History API endpoints — user's past analyses."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_required
from app.db import get_db
from app.models.analysis import Analysis
from app.models.user import User

router = APIRouter(prefix="/history", tags=["History"])


@router.get("")
async def get_history(
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0,
):
    """List the current user's past analyses."""
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    analyses = result.scalars().all()

    return {
        "items": [
            {
                "id": str(a.id),
                "input_type": a.input_type,
                "input_url": a.input_url,
                "document_title": a.document_title,
                "status": a.status,
                "overall_score": a.result.get("overall_score") if a.result else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in analyses
        ],
        "total": len(analyses),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{analysis_id}")
async def get_history_item(
    analysis_id: str,
    current_user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific past analysis (must belong to the user)."""
    try:
        uid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(400, "Invalid analysis ID.")

    result = await db.execute(
        select(Analysis).where(
            Analysis.id == uid,
            Analysis.user_id == current_user.id,
        )
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(404, "Analysis not found.")

    return {
        "id": str(analysis.id),
        "input_type": analysis.input_type,
        "input_url": analysis.input_url,
        "document_title": analysis.document_title,
        "status": analysis.status,
        "result": analysis.result,
        "error": analysis.error_message,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }
