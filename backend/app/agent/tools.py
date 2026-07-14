"""The 5 CRM agent tools.

Each tool is a plain async function operating over a DB session. They are the
concrete capabilities the LangGraph agent orchestrates. Two are called out in
the brief and implemented in detail:

  1. log_interaction  — capture + LLM summarise/extract + persist
  2. edit_interaction — modify a logged interaction (structured or NL patch)
  3. get_interaction_history
  4. get_hcp_details
  5. schedule_followup

They are also reused directly by the REST layer (the form-mode POST calls
log_interaction; the edit modal calls edit_interaction), so the AI logic lives
in exactly one place.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import EDIT_SYSTEM, EXTRACT_SYSTEM
from app.llm.client import get_llm
from app.models import FollowUp, HCP, Interaction

_ALLOWED_TYPES = {"call", "visit", "email", "virtual"}
_ALLOWED_SENTIMENT = {"positive", "neutral", "negative"}
_EDITABLE_FIELDS = {
    "interaction_type",
    "channel",
    "products_discussed",
    "samples_dropped",
    "sentiment",
    "key_topics",
    "follow_up_needed",
    "summary",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────
# Heuristic fallback used when the LLM is offline or returns nothing, so the
# tool always produces a usable structured record.
# ──────────────────────────────────────────────────────────────────────────
# Leading command phrases a rep might type in chat ("log a call with…",
# "record that…") that shouldn't appear in the stored CRM summary.
_COMMAND_PREFIX = re.compile(
    r"^\s*(?:please\s+)?"
    r"(?:log|record|note|add|capture|save|create|make)"
    r"(?:\s+(?:a|an|this|the|that|down))?"
    r"(?:\s+(?:new|quick))?"
    r"(?:\s+(?:interaction|call|visit|email|meeting|note|entry))?"
    r"(?:\s+(?:with|for|that|about|:|-|,))?\s+",
    re.IGNORECASE,
)


def _clean_summary(notes: str) -> str:
    """Best-effort readable summary for offline mode: drop a leading command
    verb and capitalise, so a chat message like 'log a call, discussed dosing'
    is stored as 'Discussed dosing' rather than echoing the instruction."""
    text = _COMMAND_PREFIX.sub("", notes.strip(), count=1).strip()
    if not text:
        text = notes.strip()
    if text:
        text = text[0].upper() + text[1:]
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    return text


def _heuristic_extract(notes: str) -> dict[str, Any]:
    low = notes.lower()
    if any(w in low for w in ("zoom", "teams", "virtual", "video call", "webex")):
        itype = "virtual"
    elif any(w in low for w in ("email", "e-mail", "mailed")):
        itype = "email"
    elif any(w in low for w in ("visit", "in person", "in-person", "office", "clinic", "booth")):
        itype = "visit"
    else:
        itype = "call"

    if any(w in low for w in ("positive", "receptive", "keen", "interested", "great", "excited", "enthusiastic")):
        sentiment = "positive"
    elif any(w in low for w in ("negative", "annoyed", "not interested", "declined", "concern", "unhappy", "rejected")):
        sentiment = "negative"
    else:
        sentiment = "neutral"

    samples = []
    for m in re.finditer(r"([A-Z][A-Za-z0-9\-]+)\s*(?:x\s*|×\s*)(\d+)", notes):
        samples.append(f"{m.group(1)} x{m.group(2)}")
    follow = any(w in low for w in ("follow up", "follow-up", "followup", "next month", "next week", "call back", "revisit", "schedule"))

    summary = _clean_summary(notes)

    return {
        "interaction_type": itype,
        "channel": "",
        "products_discussed": [],
        "samples_dropped": samples,
        "sentiment": sentiment,
        "key_topics": [],
        "follow_up_needed": follow,
        "summary": summary,
    }


def _heuristic_edit(instruction: str, current: dict[str, Any]) -> dict[str, Any]:
    """Rule-based NL-edit fallback used when the LLM is offline/returns nothing,
    so common corrections still work in a keyless demo."""
    low = instruction.lower()
    patch: dict[str, Any] = {}
    for s in _ALLOWED_SENTIMENT:
        if s in low:
            patch["sentiment"] = s
            break
    for t in _ALLOWED_TYPES:
        if t in low:
            patch["interaction_type"] = t
            break
    if any(w in low for w in ("needs follow", "flag follow", "follow up needed", "schedule a follow")):
        patch["follow_up_needed"] = True
    if any(w in low for w in ("no follow", "remove follow", "no need to follow")):
        patch["follow_up_needed"] = False
    # "add <x> to topics" / "note that we discussed <x>"
    m = re.search(r"(?:add|note|discussed|mention(?:ed)?)\s+(.+?)(?:\s+to\s+topics)?$", low)
    if m and ("topic" in low or "discuss" in low or "note" in low or "mention" in low):
        phrase = m.group(1).strip(" .")
        if phrase and len(phrase) < 60:
            patch["key_topics"] = list(dict.fromkeys((current.get("key_topics") or []) + [phrase]))
    return patch


def _clean_extraction(data: dict[str, Any], notes: str) -> dict[str, Any]:
    """Validate/normalise LLM output, backfilling from heuristics."""
    base = _heuristic_extract(notes)
    out = {**base}
    if isinstance(data, dict):
        for k in base:
            if k in data and data[k] not in (None, "", [], {}):
                out[k] = data[k]
    if out["interaction_type"] not in _ALLOWED_TYPES:
        out["interaction_type"] = base["interaction_type"]
    if out["sentiment"] not in _ALLOWED_SENTIMENT:
        out["sentiment"] = base["sentiment"]
    for list_field in ("products_discussed", "samples_dropped", "key_topics"):
        if not isinstance(out.get(list_field), list):
            out[list_field] = []
    out["follow_up_needed"] = bool(out.get("follow_up_needed"))
    return out


# ──────────────────────────────────────────────────────────────────────────
# TOOL 1 — log_interaction  (detailed, per the brief)
# ──────────────────────────────────────────────────────────────────────────
async def log_interaction(
    session: AsyncSession,
    *,
    hcp_id: int,
    raw_notes: str = "",
    rep_name: str = "Field Rep",
    source: str = "chat",
    overrides: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Capture an interaction.

    Pipeline: raw notes -> gemma2-9b-it (JSON mode) summarisation + entity
    extraction -> validated/normalised fields -> merged with any rep-provided
    `overrides` (rep values win) -> persisted Interaction row -> dict.
    """
    hcp = await session.get(HCP, hcp_id)
    if hcp is None:
        return {"error": f"No HCP with id {hcp_id}"}

    overrides = overrides or {}

    extracted: dict[str, Any] = {}
    if raw_notes.strip():
        llm = get_llm()
        extracted = await llm.json_chat(
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"HCP: {hcp.name} ({hcp.specialty}, {hcp.institution}). "
                        f"Rep notes:\n{raw_notes}"
                    ),
                },
            ]
        )
    fields = _clean_extraction(extracted, raw_notes)

    # Rep-provided structured fields win over the LLM's guesses.
    for k, v in overrides.items():
        if v not in (None, "", []):
            fields[k] = v

    interaction = Interaction(
        hcp_id=hcp_id,
        rep_name=rep_name,
        interaction_type=fields["interaction_type"],
        interaction_date=overrides.get("interaction_date") or _utcnow(),
        channel=fields.get("channel", ""),
        products_discussed=fields["products_discussed"],
        samples_dropped=fields["samples_dropped"],
        sentiment=fields["sentiment"],
        key_topics=fields["key_topics"],
        summary=fields["summary"],
        raw_notes=raw_notes,
        follow_up_needed=fields["follow_up_needed"],
        source=source,
    )
    session.add(interaction)
    await session.flush()
    await session.refresh(interaction, attribute_names=["hcp"])
    return interaction.to_dict()


# ──────────────────────────────────────────────────────────────────────────
# TOOL 2 — edit_interaction  (detailed, per the brief)
# ──────────────────────────────────────────────────────────────────────────
async def edit_interaction(
    session: AsyncSession,
    *,
    interaction_id: Optional[int] = None,
    hcp_id: Optional[int] = None,
    instruction: str = "",
    patch: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Modify a logged interaction.

    Two modes:
      * Structured (`patch`): the form edit modal passes explicit field changes.
      * Natural language (`instruction`): gemma2 reads the current record + the
        instruction and returns a field-level patch, which is validated against
        the allow-list before being applied.
    If no interaction_id is given, the HCP's most recent interaction is edited
    (matches the conversational "actually, change that..." flow).
    """
    interaction: Optional[Interaction] = None
    if interaction_id is not None:
        interaction = await session.get(Interaction, interaction_id)
    elif hcp_id is not None:
        res = await session.execute(
            select(Interaction)
            .where(Interaction.hcp_id == hcp_id)
            .order_by(Interaction.created_at.desc())
            .limit(1)
        )
        interaction = res.scalar_one_or_none()

    if interaction is None:
        return {"error": "No matching interaction to edit."}

    # Eager-load the hcp relationship so later to_dict() calls don't trigger a
    # lazy load outside the async greenlet context.
    await session.refresh(interaction, attribute_names=["hcp"])

    effective_patch: dict[str, Any] = dict(patch or {})

    if not effective_patch and instruction.strip():
        llm = get_llm()
        current = interaction.to_dict()
        effective_patch = await llm.json_chat(
            messages=[
                {"role": "system", "content": EDIT_SYSTEM},
                {
                    "role": "user",
                    "content": f"Current record:\n{current}\n\nInstruction: {instruction}",
                },
            ]
        )
        if not effective_patch:  # offline / LLM returned nothing → heuristic
            effective_patch = _heuristic_edit(instruction, current)

    applied: dict[str, Any] = {}
    for field, value in (effective_patch or {}).items():
        if field not in _EDITABLE_FIELDS:
            continue
        if field == "interaction_type" and value not in _ALLOWED_TYPES:
            continue
        if field == "sentiment" and value not in _ALLOWED_SENTIMENT:
            continue
        setattr(interaction, field, value)
        applied[field] = value

    await session.flush()
    await session.refresh(interaction, attribute_names=["hcp"])
    result = interaction.to_dict()
    result["_applied"] = applied
    return result


# ──────────────────────────────────────────────────────────────────────────
# TOOL 3 — get_interaction_history
# ──────────────────────────────────────────────────────────────────────────
async def get_interaction_history(
    session: AsyncSession, *, hcp_id: int, limit: int = 10
) -> dict[str, Any]:
    res = await session.execute(
        select(Interaction)
        .where(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.interaction_date.desc())
        .limit(limit)
    )
    rows = res.scalars().all()
    for r in rows:
        await session.refresh(r, attribute_names=["hcp"])
    return {"count": len(rows), "interactions": [r.to_dict() for r in rows]}


# ──────────────────────────────────────────────────────────────────────────
# TOOL 4 — get_hcp_details
# ──────────────────────────────────────────────────────────────────────────
async def get_hcp_details(
    session: AsyncSession, *, hcp_id: Optional[int] = None, name: Optional[str] = None
) -> dict[str, Any]:
    hcp: Optional[HCP] = None
    if hcp_id is not None:
        hcp = await session.get(HCP, hcp_id)
    if hcp is None and name:
        res = await session.execute(
            select(HCP).where(HCP.name.ilike(f"%{name.strip()}%")).limit(1)
        )
        hcp = res.scalar_one_or_none()
    if hcp is None:
        return {"error": "HCP not found."}
    return hcp.to_dict()


# ──────────────────────────────────────────────────────────────────────────
# TOOL 5 — schedule_followup
# ──────────────────────────────────────────────────────────────────────────
async def schedule_followup(
    session: AsyncSession,
    *,
    hcp_id: int,
    purpose: str = "",
    in_days: int = 14,
    interaction_id: Optional[int] = None,
) -> dict[str, Any]:
    hcp = await session.get(HCP, hcp_id)
    if hcp is None:
        return {"error": f"No HCP with id {hcp_id}"}
    try:
        in_days = int(in_days)
    except (TypeError, ValueError):
        in_days = 14
    due = _utcnow() + timedelta(days=max(0, in_days))
    fu = FollowUp(
        hcp_id=hcp_id,
        interaction_id=interaction_id,
        due_date=due,
        purpose=purpose or "Follow-up visit",
        status="open",
    )
    session.add(fu)
    await session.flush()
    return fu.to_dict()
