"""Dashboard aggregates — a single call that powers the overview screen.

Returns headline counts plus breakdowns (sentiment, tier, interaction type)
and a cross-HCP recent-activity feed, computed from the same three tables.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.db.session import session_scope
from app.models import FollowUp, HCP, Interaction

router = APIRouter()


def _counts(rows: list[tuple], keys: list[str]) -> dict[str, int]:
    """Turn (value, count) rows into a dict pre-seeded with every key at 0."""
    out = {k: 0 for k in keys}
    for value, count in rows:
        out[value] = count
    return out


@router.get("")
async def dashboard_stats() -> dict:
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    async with session_scope() as s:
        hcp_count = (await s.execute(select(func.count(HCP.id)))).scalar_one()
        interaction_count = (
            await s.execute(select(func.count(Interaction.id)))
        ).scalar_one()

        sentiment_rows = (
            await s.execute(
                select(Interaction.sentiment, func.count(Interaction.id)).group_by(
                    Interaction.sentiment
                )
            )
        ).all()
        type_rows = (
            await s.execute(
                select(Interaction.interaction_type, func.count(Interaction.id)).group_by(
                    Interaction.interaction_type
                )
            )
        ).all()
        tier_rows = (
            await s.execute(
                select(HCP.tier, func.count(HCP.id)).group_by(HCP.tier)
            )
        ).all()

        followups_open = (
            await s.execute(
                select(func.count(FollowUp.id)).where(FollowUp.status == "open")
            )
        ).scalar_one()
        followups_flagged = (
            await s.execute(
                select(func.count(Interaction.id)).where(
                    Interaction.follow_up_needed.is_(True)
                )
            )
        ).scalar_one()
        logged_this_week = (
            await s.execute(
                select(func.count(Interaction.id)).where(
                    Interaction.interaction_date >= week_ago
                )
            )
        ).scalar_one()

        recent_res = await s.execute(
            select(Interaction)
            .order_by(Interaction.interaction_date.desc())
            .limit(8)
        )
        recent = recent_res.scalars().all()
        for r in recent:
            await s.refresh(r, attribute_names=["hcp"])
        recent_activity = [r.to_dict() for r in recent]

    return {
        "hcp_count": hcp_count,
        "interaction_count": interaction_count,
        "logged_this_week": logged_this_week,
        "followups_open": followups_open,
        "followups_flagged": followups_flagged,
        "sentiment": _counts(sentiment_rows, ["positive", "neutral", "negative"]),
        "interaction_types": _counts(type_rows, ["call", "visit", "email", "virtual"]),
        "tiers": _counts(tier_rows, ["A", "B", "C"]),
        "recent_activity": recent_activity,
    }
