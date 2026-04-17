"""Main API router — mounts all sub-routers."""

from fastapi import APIRouter

from app.api.analyze import router as analyze_router
from app.api.auth import router as auth_router
from app.api.history import router as history_router

api_router = APIRouter(prefix="/api")
api_router.include_router(analyze_router)
api_router.include_router(auth_router)
api_router.include_router(history_router)
