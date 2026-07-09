"""HCP directory endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.session import session_scope
from app.models import HCP

router = APIRouter()


@router.get("")
async def list_hcps() -> list[dict]:
    async with session_scope() as s:
        res = await s.execute(select(HCP).order_by(HCP.name))
        return [h.to_dict() for h in res.scalars().all()]


@router.get("/{hcp_id}")
async def get_hcp(hcp_id: int) -> dict:
    async with session_scope() as s:
        hcp = await s.get(HCP, hcp_id)
        if hcp is None:
            raise HTTPException(status_code=404, detail="HCP not found")
        return hcp.to_dict()
