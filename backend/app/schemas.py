"""Pydantic request/response models for the API layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Sentiment = Literal["positive", "neutral", "negative"]
InteractionType = Literal["call", "visit", "email", "virtual"]


class InteractionCreate(BaseModel):
    """Form-mode submission. `raw_notes` triggers AI enrichment; any structured
    field the rep fills in explicitly wins over the LLM's extraction."""

    hcp_id: int
    rep_name: str = "Field Rep"
    raw_notes: str = ""
    interaction_type: Optional[InteractionType] = None
    interaction_date: Optional[datetime] = None
    channel: Optional[str] = None
    products_discussed: Optional[list[str]] = None
    samples_dropped: Optional[list[str]] = None
    sentiment: Optional[Sentiment] = None
    key_topics: Optional[list[str]] = None
    summary: Optional[str] = None
    follow_up_needed: Optional[bool] = None
    enrich: bool = True  # run the LangGraph log_interaction tool / LLM enrichment


class InteractionUpdate(BaseModel):
    """Structured (form) edit — only the provided fields change."""

    interaction_type: Optional[InteractionType] = None
    interaction_date: Optional[datetime] = None
    channel: Optional[str] = None
    products_discussed: Optional[list[str]] = None
    samples_dropped: Optional[list[str]] = None
    sentiment: Optional[Sentiment] = None
    key_topics: Optional[list[str]] = None
    summary: Optional[str] = None
    follow_up_needed: Optional[bool] = None


class ChatRequest(BaseModel):
    message: str
    hcp_id: Optional[int] = None
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    tool_result: Optional[Any] = None
    hcp_id: Optional[int] = None
