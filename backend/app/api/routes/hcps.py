"""HCP directory endpoints — list, get, create and delete.

Creating and deleting HCPs from the UI means the app needs no seeded demo
data: a rep builds their own real HCP directory in the app.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import delete, select

from app.db.session import session_scope
from app.models import FollowUp, HCP
from app.schemas import HCPCreate

router = APIRouter()


@router.get("")
async def list_hcps() -> list[dict]:
    async with session_scope() as s:
        res = await s.execute(select(HCP).order_by(HCP.name))
        return [h.to_dict() for h in res.scalars().all()]


@router.post("", status_code=201)
async def create_hcp(payload: HCPCreate) -> dict:
    async with session_scope() as s:
        hcp = HCP(
            name=payload.name.strip(),
            specialty=payload.specialty.strip(),
            institution=payload.institution.strip(),
            tier=payload.tier,
            preferred_products=[p.strip() for p in payload.preferred_products if p.strip()],
            email=payload.email.strip(),
            city=payload.city.strip(),
        )
        s.add(hcp)
        await s.flush()
        return hcp.to_dict()


@router.get("/{hcp_id}")
async def get_hcp(hcp_id: int) -> dict:
    async with session_scope() as s:
        hcp = await s.get(HCP, hcp_id)
        if hcp is None:
            raise HTTPException(status_code=404, detail="HCP not found")
        return hcp.to_dict()


@router.delete("/{hcp_id}", status_code=204, response_class=Response)
async def delete_hcp(hcp_id: int) -> Response:
    """Delete an HCP and all their interactions (cascade)."""
    async with session_scope() as s:
        hcp = await s.get(HCP, hcp_id)
        if hcp is None:
            raise HTTPException(status_code=404, detail="HCP not found")
        # Remove follow-ups first (they FK to both hcp and interactions);
        # interactions themselves cascade via the HCP relationship.
        await s.execute(delete(FollowUp).where(FollowUp.hcp_id == hcp_id))
        await s.delete(hcp)
    return Response(status_code=204)
