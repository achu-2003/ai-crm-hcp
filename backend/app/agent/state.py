"""LangGraph agent state — a TypedDict flowing through the graph nodes.

Each node receives the state and returns a partial-state dict that LangGraph
merges in (the same pattern used in job7_chatbot/app/agent/runtime.py).
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # Inputs
    user_message: str
    hcp_id: Optional[int]
    history: list[dict[str, str]]

    # Populated by load_context
    context: dict[str, Any]

    # Populated by router
    decision: dict[str, Any]  # {"tool": ..., "args": {...}, "rationale": ...}

    # Populated by execute_tool
    tool_used: Optional[str]
    tool_result: Any

    # Populated by responder
    reply: str
