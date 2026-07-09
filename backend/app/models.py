"""SQLAlchemy ORM models for the HCP CRM module.

Three tables: HCP (the healthcare professional), Interaction (a logged
touchpoint) and FollowUp (a scheduled next action). JSON columns use the
portable SQLAlchemy JSON type so they work on both Postgres and SQLite.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class HCP(Base):
    __tablename__ = "hcps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str] = mapped_column(String(120), default="")
    institution: Mapped[str] = mapped_column(String(200), default="")
    tier: Mapped[str] = mapped_column(String(2), default="B")  # A / B / C
    preferred_products: Mapped[list] = mapped_column(JSON, default=list)
    email: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(120), default="")

    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="hcp", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "institution": self.institution,
            "tier": self.tier,
            "preferred_products": self.preferred_products or [],
            "email": self.email,
            "city": self.city,
        }


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), nullable=False, index=True)
    rep_name: Mapped[str] = mapped_column(String(120), default="Field Rep")
    interaction_type: Mapped[str] = mapped_column(String(40), default="call")  # call/visit/email/virtual
    interaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    channel: Mapped[str] = mapped_column(String(60), default="")
    products_discussed: Mapped[list] = mapped_column(JSON, default=list)
    samples_dropped: Mapped[list] = mapped_column(JSON, default=list)
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")  # positive/neutral/negative
    key_topics: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    raw_notes: Mapped[str] = mapped_column(Text, default="")
    follow_up_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(10), default="form")  # form / chat
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    hcp: Mapped["HCP"] = relationship(back_populates="interactions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hcp_id": self.hcp_id,
            "hcp_name": self.hcp.name if self.hcp else None,
            "rep_name": self.rep_name,
            "interaction_type": self.interaction_type,
            "interaction_date": self.interaction_date.isoformat() if self.interaction_date else None,
            "channel": self.channel,
            "products_discussed": self.products_discussed or [],
            "samples_dropped": self.samples_dropped or [],
            "sentiment": self.sentiment,
            "key_topics": self.key_topics or [],
            "summary": self.summary,
            "raw_notes": self.raw_notes,
            "follow_up_needed": self.follow_up_needed,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"), nullable=False, index=True)
    interaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("interactions.id"), nullable=True
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    purpose: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open / done
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hcp_id": self.hcp_id,
            "interaction_id": self.interaction_id,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "purpose": self.purpose,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
