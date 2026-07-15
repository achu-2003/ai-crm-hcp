"""Pydantic request/response models for the API layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Sentiment = Literal["positive", "neutral", "negative"]
InteractionType = Literal["call", "visit", "email", "virtual", "meeting"]
Tier = Literal["A", "B", "C"]


class HCPCreate(BaseModel):
    """Create a Healthcare Professional from the UI (replaces demo seed data)."""

    name: str = Field(min_length=1, max_length=200)
    specialty: str = ""
    institution: str = ""
    tier: Tier = "B"
    preferred_products: list[str] = Field(default_factory=list)
    email: str = ""
    city: str = ""


class InteractionCreate(BaseModel):
    """Form-mode submission. `raw_notes` triggers AI enrichment; any structured
    field the rep fills in explicitly wins over the LLM's extraction."""

    hcp_id: int
    rep_name: str = "Field Rep"
    raw_notes: str = ""
    interaction_type: Optional[InteractionType] = None
    interaction_date: Optional[datetime] = None
    channel: Optional[str] = None
    attendees: Optional[list[str]] = None
    products_discussed: Optional[list[str]] = None
    materials_shared: Optional[list[str]] = None
    samples_dropped: Optional[list[str]] = None
    sentiment: Optional[Sentiment] = None
    key_topics: Optional[list[str]] = None
    topics_discussed: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    summary: Optional[str] = None
    follow_up_needed: Optional[bool] = None
    consent_obtained: Optional[bool] = None
    source: Optional[Literal["form", "chat", "voice"]] = None
    enrich: bool = True  # run the LangGraph log_interaction tool / LLM enrichment


class InteractionUpdate(BaseModel):
    """Structured (form) edit — only the provided fields change."""

    interaction_type: Optional[InteractionType] = None
    interaction_date: Optional[datetime] = None
    channel: Optional[str] = None
    attendees: Optional[list[str]] = None
    products_discussed: Optional[list[str]] = None
    materials_shared: Optional[list[str]] = None
    samples_dropped: Optional[list[str]] = None
    sentiment: Optional[Sentiment] = None
    key_topics: Optional[list[str]] = None
    topics_discussed: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    summary: Optional[str] = None
    follow_up_needed: Optional[bool] = None


class ExtractRequest(BaseModel):
    """Draft-only extraction: turn free text (typed notes or a voice transcript)
    into structured fields for the form WITHOUT persisting anything. The rep
    reviews the draft and submits it themselves."""

    text: str
    hcp_id: Optional[int] = None
    consent_obtained: bool = False


class FollowUpUpdate(BaseModel):
    """Mark a follow-up done / reword its purpose."""

    status: Optional[Literal["open", "done"]] = None
    purpose: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    hcp_id: Optional[int] = None
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None
    hcp_id: Optional[int] = None
