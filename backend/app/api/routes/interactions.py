"""Interaction CRUD — the structured (form) side of the Log Interaction screen.

Create runs the same `log_interaction` agent tool the chat uses (so form
submissions get AI summary + entity extraction). Update runs `edit_interaction`
with a structured patch.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.agent import tools
from app.db.session import session_scope
from app.models import Interaction
from app.schemas import ExtractRequest, InteractionCreate, InteractionUpdate

router = APIRouter()

# Fields the rep can set explicitly on the form; anything they leave blank is
# filled by the LLM extraction inside log_interaction.
_OVERRIDABLE = (
    "interaction_type",
    "interaction_date",
    "channel",
    "attendees",
    "products_discussed",
    "materials_shared",
    "samples_dropped",
    "sentiment",
    "key_topics",
    "topics_discussed",
    "outcomes",
    "follow_up_actions",
    "summary",
    "follow_up_needed",
    "consent_obtained",
)


@router.get("")
async def list_interactions(hcp_id: int | None = Query(default=None)) -> list[dict]:
    async with session_scope() as s:
        stmt = select(Interaction).order_by(Interaction.interaction_date.desc())
        if hcp_id is not None:
            stmt = stmt.where(Interaction.hcp_id == hcp_id)
        res = await s.execute(stmt)
        rows = res.scalars().all()
        for r in rows:
            await s.refresh(r, attribute_names=["hcp"])
        return [r.to_dict() for r in rows]


@router.post("/extract")
async def extract_interaction(payload: ExtractRequest) -> dict:
    """Draft-only: free text → structured fields, nothing persisted.

    This is what lets the AI fill the form and leave the rep in control — the
    form binds to the returned draft, and the DB is only touched when the rep
    actually submits. Also backs the voice-note path, which is why consent is
    echoed back on the draft.
    """
    async with session_scope() as s:
        draft = await tools.draft_interaction(
            s, hcp_id=payload.hcp_id, raw_notes=payload.text
        )
    draft["consent_obtained"] = payload.consent_obtained
    return draft


@router.post("")
async def create_interaction(payload: InteractionCreate) -> dict:
    """Form submit → log_interaction tool (AI-enriched when enrich=True)."""
    overrides: dict = {}
    for field in _OVERRIDABLE:
        val = getattr(payload, field)
        if val is not None:
            overrides[field] = val

    async with session_scope() as s:
        result = await tools.log_interaction(
            s,
            hcp_id=payload.hcp_id,
            raw_notes=payload.raw_notes if payload.enrich else "",
            rep_name=payload.rep_name,
            source=payload.source or "form",
            overrides=overrides,
        )
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{interaction_id}")
async def get_interaction(interaction_id: int) -> dict:
    async with session_scope() as s:
        row = await s.get(Interaction, interaction_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Interaction not found")
        await s.refresh(row, attribute_names=["hcp"])
        return row.to_dict()


@router.patch("/{interaction_id}")
async def update_interaction(interaction_id: int, payload: InteractionUpdate) -> dict:
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    async with session_scope() as s:
        result = await tools.edit_interaction(
            s, interaction_id=interaction_id, patch=patch
        )
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
