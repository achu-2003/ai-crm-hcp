"""Follow-up endpoints.

Surfaces the FollowUp rows created by the `schedule_followup` agent tool so
they're visible in the UI (next-best-action list), and lets a rep mark one done.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.db.session import session_scope
from app.models import FollowUp
from app.schemas import FollowUpUpdate

router = APIRouter()


@router.get("")
async def list_followups(
    hcp_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[dict]:
    async with session_scope() as s:
        stmt = select(FollowUp).order_by(FollowUp.due_date.asc())
        if hcp_id is not None:
            stmt = stmt.where(FollowUp.hcp_id == hcp_id)
        if status is not None:
            stmt = stmt.where(FollowUp.status == status)
        res = await s.execute(stmt)
        return [f.to_dict() for f in res.scalars().all()]


@router.patch("/{followup_id}")
async def update_followup(followup_id: int, payload: FollowUpUpdate) -> dict:
    async with session_scope() as s:
        fu = await s.get(FollowUp, followup_id)
        if fu is None:
            raise HTTPException(status_code=404, detail="Follow-up not found")
        if payload.status is not None:
            fu.status = payload.status
        if payload.purpose is not None:
            fu.purpose = payload.purpose
        await s.flush()
        return fu.to_dict()
