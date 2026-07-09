"""Health + capability probe."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "llm_model": s.llm_model_chat,
        "llm_router_model": s.llm_model_router,
        "llm_configured": s.llm_configured,
        "database": "postgres" if s.database_url.startswith("postgresql") else "sqlite",
    }
