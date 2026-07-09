"""Conversational endpoint — drives the LangGraph agent."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    agent = request.app.state.agent
    result = await agent.ainvoke(
        message=payload.message,
        hcp_id=payload.hcp_id,
        history=payload.history,
    )
    return ChatResponse(**result)
