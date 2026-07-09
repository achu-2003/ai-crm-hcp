"""Application settings — single source of truth, loaded from .env.

Mirrors the pydantic-settings pattern used across the codebase
(job7_chatbot / shescale-whatsapp-bot): a cached Settings() with typed
fields and AliasChoices so OPENAI_* env names also work.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM (Groq via OpenAI-compatible endpoint) ──
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENAI_BASE_URL"),
    )
    llm_model_chat: str = Field(
        default="gemma2-9b-it",
        validation_alias=AliasChoices("LLM_MODEL_CHAT", "OPENAI_MODEL_CHAT"),
    )
    # Router/tool-selection node. Defaults to the chat model; can be pointed at
    # llama-3.3-70b-versatile for stronger reasoning without any code change.
    llm_model_router: str = Field(
        default="gemma2-9b-it",
        validation_alias=AliasChoices("LLM_MODEL_ROUTER",),
    )
    llm_timeout_seconds: float = Field(default=30.0)
    llm_max_retries: int = Field(default=3)

    # ── Database ──
    database_url: str = Field(
        default="sqlite+aiosqlite:///./crm.db",
        validation_alias=AliasChoices("DATABASE_URL",),
    )

    # ── CORS ──
    cors_allow_origins: str = Field(
        default="http://localhost:5173,http://localhost:4173,http://localhost:3000",
        validation_alias=AliasChoices("CORS_ALLOW_ORIGINS",),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        """True when a real Groq key is present (not the placeholder)."""
        return bool(self.llm_api_key) and "replace_me" not in self.llm_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
