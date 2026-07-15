"""LangGraph StateGraph for the HCP CRM agent.

Flow (bounded, single tool hop per turn):

    START -> load_context -> router -> execute_tool -> responder -> END

The router node asks gemma2-9b-it (JSON mode) which tool to run; execute_tool
dispatches to app/agent/tools.py inside a DB transaction; responder writes the
rep-facing reply. The graph is compiled once at startup and stored on
app.state.agent (see main.py).

Pattern adapted from job7_chatbot/app/agent/runtime.py (_build_graph).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agent import tools
from app.agent.prompts import RESPONDER_SYSTEM, ROUTER_SYSTEM
from app.agent.state import AgentState
from app.db.session import session_scope
from app.llm.client import get_llm

log = logging.getLogger("crm.agent")

_VALID_TOOLS = {
    "log_interaction",
    "edit_interaction",
    "get_interaction_history",
    "get_hcp_details",
    "schedule_followup",
    "chitchat",
}


class AgentRuntime:
    def __init__(self) -> None:
        self._llm = get_llm()
        self._graph = self._build_graph()

    # ── Graph wiring ──────────────────────────────────────────────────────
    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("load_context", self._load_context)
        g.add_node("router", self._router)
        g.add_node("execute_tool", self._execute_tool)
        g.add_node("responder", self._responder)

        g.add_edge(START, "load_context")
        g.add_edge("load_context", "router")
        g.add_edge("router", "execute_tool")
        g.add_edge("execute_tool", "responder")
        g.add_edge("responder", END)
        return g.compile()

    # ── Nodes ─────────────────────────────────────────────────────────────
    async def _load_context(self, state: AgentState) -> dict[str, Any]:
        hcp_id = state.get("hcp_id")
        context: dict[str, Any] = {}
        if hcp_id:
            async with session_scope() as s:
                context["hcp"] = await tools.get_hcp_details(s, hcp_id=hcp_id)
                hist = await tools.get_interaction_history(s, hcp_id=hcp_id, limit=3)
                context["recent"] = hist["interactions"]
        return {"context": context}

    async def _router(self, state: AgentState) -> dict[str, Any]:
        hcp = state.get("context", {}).get("hcp", {})
        recent = state.get("context", {}).get("recent", [])
        recent_ids = [r["id"] for r in recent]
        user_ctx = (
            f"Selected HCP: {hcp.get('name', 'none')} "
            f"(id={hcp.get('id')}, {hcp.get('specialty', '')}). "
            f"Recent interaction ids: {recent_ids}.\n\n"
            f"Rep message: {state['user_message']}"
        )
        decision = await self._llm.json_chat(
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM},
                {"role": "user", "content": user_ctx},
            ],
            model=get_llm()._settings.llm_model_router,
        )
        tool = decision.get("tool")
        if tool not in _VALID_TOOLS:
            # Offline / malformed: infer a sane default from the message.
            tool = self._fallback_tool(state["user_message"])
            decision = {"tool": tool, "args": {}, "rationale": "fallback"}
        decision["tool"] = tool
        return {"decision": decision}

    async def _execute_tool(self, state: AgentState) -> dict[str, Any]:
        decision = state["decision"]
        tool = decision["tool"]
        args = decision.get("args") or {}
        hcp_id = state.get("hcp_id")
        recent = state.get("context", {}).get("recent", [])
        result: Any = None

        async with session_scope() as s:
            if tool == "log_interaction":
                notes = args.get("notes") or state["user_message"]
                result = await tools.log_interaction(
                    s, hcp_id=hcp_id, raw_notes=notes, source="chat"
                )
            elif tool == "edit_interaction":
                iid = args.get("interaction_id")
                if not iid and recent:
                    iid = recent[0]["id"]
                result = await tools.edit_interaction(
                    s,
                    interaction_id=iid,
                    hcp_id=hcp_id,
                    instruction=args.get("instruction") or state["user_message"],
                )
            elif tool == "get_interaction_history":
                result = await tools.get_interaction_history(s, hcp_id=hcp_id)
            elif tool == "get_hcp_details":
                result = await tools.get_hcp_details(
                    s, hcp_id=hcp_id, name=args.get("name")
                )
            elif tool == "schedule_followup":
                result = await tools.schedule_followup(
                    s,
                    hcp_id=hcp_id,
                    purpose=args.get("purpose", ""),
                    in_days=args.get("in_days", 14),
                    interaction_id=(recent[0]["id"] if recent else None),
                )
            else:  # chitchat
                result = {"note": "no tool executed"}

        return {"tool_used": tool, "tool_result": result}

    async def _responder(self, state: AgentState) -> dict[str, Any]:
        tool = state.get("tool_used")
        result = state.get("tool_result")

        # Deterministic reply when the LLM is offline, so the demo still reads well.
        if self._llm.offline:
            return {"reply": self._offline_reply(tool, result, state)}

        reply = await self._llm.chat(
            messages=[
                {"role": "system", "content": RESPONDER_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Rep message: {state['user_message']}\n"
                        f"Tool run: {tool}\n"
                        f"Tool result (JSON): {result}"
                    ),
                },
            ],
            temperature=0.4,
            max_tokens=250,
        )
        return {"reply": reply.strip() or self._offline_reply(tool, result, state)}

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _fallback_tool(message: str) -> str:
        """Deterministic intent guess used only in OFFLINE mode (no LLM router).

        Precedence matters: an explicit leading command verb wins, so
        "log a visit ... wants a follow-up" is a LOG (not a schedule) even
        though it mentions a follow-up, while "schedule a follow-up" still
        routes to scheduling.
        """
        low = message.strip().lower()
        # 1) Explicit "log/record this…" always means capture an interaction.
        if re.match(r"^(log|record|capture|save)\b", low):
            return "log_interaction"
        # 2) Corrections to an existing record.
        if any(w in low for w in ("change", "edit", "update", "correct", "actually", "instead", "rename")):
            return "edit_interaction"
        # 3) Asking about past interactions.
        if any(w in low for w in ("history", "last time", "previous", "what did", "recently", "what have we")):
            return "get_interaction_history"
        # 4) Scheduling — needs a scheduling verb up front or an explicit phrase,
        #    not just the words "follow up" appearing anywhere in the notes.
        if re.match(r"^(schedule|book|plan|set up|set a|remind)\b", low) or any(
            p in low for p in ("schedule a follow", "book a follow", "set a follow", "next visit", "plan a follow")
        ):
            return "schedule_followup"
        # 5) Asking about the HCP's profile.
        if any(w in low for w in ("who is", "profile", "specialty", "tier", "details about", "tell me about")):
            return "get_hcp_details"
        # 6) Small talk.
        if any(w in low for w in ("hi", "hello", "hey", "thanks", "thank you")) and len(message) < 30:
            return "chitchat"
        return "log_interaction"

    @staticmethod
    def _offline_reply(tool: str, result: Any, state: AgentState) -> str:
        if isinstance(result, dict) and result.get("error"):
            return f"⚠️ {result['error']}"
        if tool == "log_interaction" and isinstance(result, dict):
            filled = [
                label
                for label, key in (
                    ("HCP Name", "hcp_name"),
                    ("Date", "interaction_date"),
                    ("Topics", "topics_discussed"),
                    ("Materials", "materials_shared"),
                    ("Samples", "samples_dropped"),
                    ("Sentiment", "sentiment"),
                )
                if result.get(key)
            ]
            reply = (
                "✅ Interaction logged successfully! "
                f"The details ({', '.join(filled)}) have been automatically populated "
                "on the form from your summary — have a quick look and adjust anything "
                "I got wrong."
            )
            if result.get("follow_up_needed"):
                reply += " Would you like me to schedule the follow-up?"
            return reply
        if tool == "edit_interaction" and isinstance(result, dict):
            applied = result.get("_applied", {})
            return f"✏️ Updated interaction #{result.get('id')} — changed: {', '.join(applied) or 'nothing'}."
        if tool == "get_interaction_history" and isinstance(result, dict):
            return f"📋 Found {result.get('count', 0)} recent interaction(s) for this HCP."
        if tool == "get_hcp_details" and isinstance(result, dict):
            return (
                f"👩‍⚕️ {result.get('name')} — {result.get('specialty')} at "
                f"{result.get('institution')} (Tier {result.get('tier')})."
            )
        if tool == "schedule_followup" and isinstance(result, dict):
            return f"📅 Follow-up scheduled for {str(result.get('due_date', ''))[:10]}: {result.get('purpose')}."
        if tool == "chitchat":
            hcp = state.get("context", {}).get("hcp", {})
            who = hcp.get("name")
            return (
                f"Hi! I'm your CRM assistant"
                + (f" — ready to help with {who}. " if who else ". ")
                + "Tell me about a call or visit and I'll log it, or ask what you discussed last time."
            )
        return "👍 Done."

    # ── Public entry ──────────────────────────────────────────────────────
    async def ainvoke(
        self, *, message: str, hcp_id: int | None, history: list[dict] | None = None
    ) -> dict[str, Any]:
        final = await self._graph.ainvoke(
            {
                "user_message": message,
                "hcp_id": hcp_id,
                "history": history or [],
            }
        )
        return {
            "reply": final.get("reply", ""),
            "tool_used": final.get("tool_used"),
            "tool_result": final.get("tool_result"),
            "hcp_id": hcp_id,
        }
