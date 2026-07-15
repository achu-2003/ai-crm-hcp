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

_ALLOWED_TYPES = {"call", "visit", "email", "virtual", "meeting"}
_ALLOWED_SENTIMENT = {"positive", "neutral", "negative"}
_EDITABLE_FIELDS = {
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
    "follow_up_needed",
    "summary",
}
_LIST_FIELDS = (
    "attendees",
    "products_discussed",
    "materials_shared",
    "samples_dropped",
    "key_topics",
)
_TEXT_FIELDS = ("topics_discussed", "outcomes", "follow_up_actions")

# Informational leave-behinds the rep might mention by name. Used by the
# offline heuristic; the LLM extracts these from context when it is available.
_MATERIAL_WORDS = (
    "brochure", "brochures", "leaflet", "leaflets", "reprint", "reprints",
    "deck", "slide deck", "study", "studies", "monograph", "flyer",
    "pamphlet", "whitepaper", "case study", "data pack",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    """Accept a datetime or an ISO-8601 string; reject anything else.

    The form sends a real timestamp, but the natural-language edit path routes
    through the LLM, so this must not trust its input.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


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
    elif any(w in low for w in ("meeting", "met with", "sat down with")):
        itype = "meeting"
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

    # Leave-behinds named in the notes ("shared the brochures") — deduped and
    # title-cased so they read as chips.
    materials = []
    for word in _MATERIAL_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", low):
            materials.append(word.capitalize())
    materials = list(dict.fromkeys(materials))

    follow = any(w in low for w in ("follow up", "follow-up", "followup", "next month", "next week", "call back", "revisit", "schedule"))

    summary = _clean_summary(notes)

    return {
        "interaction_type": itype,
        "channel": "",
        "attendees": [],
        "products_discussed": [],
        "materials_shared": materials,
        "samples_dropped": samples,
        "sentiment": sentiment,
        "key_topics": [],
        "topics_discussed": summary,
        "outcomes": "",
        "follow_up_actions": "",
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
    for list_field in _LIST_FIELDS:
        value = out.get(list_field)
        if not isinstance(value, list):
            out[list_field] = []
        else:
            # gemma2 sometimes returns [{"name": "..."}] instead of ["..."]
            out[list_field] = [str(v) for v in value if v not in (None, "")]
    for text_field in _TEXT_FIELDS:
        if not isinstance(out.get(text_field), str):
            out[text_field] = ""
    # The form's "Topics Discussed" box should never be blank when the model
    # did name topics — fall back to the chips, then to the summary.
    if not out["topics_discussed"].strip():
        out["topics_discussed"] = ", ".join(out["key_topics"]) or out["summary"]
    out["follow_up_needed"] = bool(out.get("follow_up_needed"))
    # A named next step implies the flag, even if the model forgot to set it.
    if out["follow_up_actions"].strip():
        out["follow_up_needed"] = True
    return out


# ──────────────────────────────────────────────────────────────────────────
# Shared extraction — used by log_interaction (persists) and by
# draft_interaction (does not).
# ──────────────────────────────────────────────────────────────────────────
async def _extract_fields(hcp: HCP, raw_notes: str) -> dict[str, Any]:
    """raw notes -> gemma2-9b-it (JSON mode) -> validated structured fields."""
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
    return _clean_extraction(extracted, raw_notes)


async def draft_interaction(
    session: AsyncSession, *, hcp_id: Optional[int] = None, raw_notes: str = ""
) -> dict[str, Any]:
    """Extract structured fields WITHOUT persisting.

    Backs the "AI fills the form, the rep confirms" flow: the typed notes or a
    voice-note transcript become a draft the rep reviews and edits before they
    submit it. Nothing reaches the DB until they do.
    """
    hcp = await session.get(HCP, hcp_id) if hcp_id is not None else None
    if hcp is None:
        # Extraction does not strictly need the HCP — it only enriches the
        # prompt — so fall back to an unnamed placeholder rather than erroring.
        hcp = HCP(name="the HCP", specialty="", institution="")
    fields = await _extract_fields(hcp, raw_notes)
    fields["raw_notes"] = raw_notes
    return fields


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

    fields = await _extract_fields(hcp, raw_notes)

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
        attendees=fields["attendees"],
        products_discussed=fields["products_discussed"],
        materials_shared=fields["materials_shared"],
        samples_dropped=fields["samples_dropped"],
        sentiment=fields["sentiment"],
        key_topics=fields["key_topics"],
        topics_discussed=fields["topics_discussed"],
        outcomes=fields["outcomes"],
        follow_up_actions=fields["follow_up_actions"],
        summary=fields["summary"],
        raw_notes=raw_notes,
        follow_up_needed=fields["follow_up_needed"],
        consent_obtained=bool(overrides.get("consent_obtained")),
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
        if field == "interaction_date":
            value = _coerce_datetime(value)
            if value is None:
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
