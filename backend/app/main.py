"""FastAPI application entrypoint.

Lifespan: create/migrate tables and build the LangGraph agent ONCE (stored on
app.state.agent). Routers are one-per-file under app/api/routes. CORS is
configured for the React dev/preview servers.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import AgentRuntime
from app.api.routes import chat, followups, health, hcps, interactions, stats
from app.config import get_settings
from app.seed import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("crm")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await init_db()  # create tables + migrate an older DB forward
    app.state.agent = AgentRuntime()  # compile the LangGraph graph once
    log.info(
        "CRM ready — model=%s router=%s llm_configured=%s",
        settings.llm_model_chat,
        settings.llm_model_router,
        settings.llm_configured,
    )
    yield


app = FastAPI(title="AI-First CRM — HCP Module", version="1.0.0", lifespan=lifespan)

_settings = get_settings()
if _settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
app.include_router(hcps.router, prefix="/api/v1/hcps", tags=["hcps"])
app.include_router(interactions.router, prefix="/api/v1/interactions", tags=["interactions"])
app.include_router(followups.router, prefix="/api/v1/followups", tags=["followups"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/")
async def root() -> dict:
    return {"service": "ai-crm-hcp", "docs": "/docs", "health": "/health"}
