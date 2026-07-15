"""Thin async wrapper over the OpenAI SDK, pointed at Groq.

Adapted from job7_chatbot/app/llm/client.py, trimmed to be self-contained
(no Prometheus/structlog deps). Talks to Groq's OpenAI-compatible endpoint
(https://api.groq.com/openai/v1) so `gemma2-9b-it` is reached with the plain
OpenAI SDK. `json_chat()` uses response_format=json_object — the key to
getting reliable structured output out of gemma2, which does NOT support
Groq's native tool-calling API.

If no Groq key is configured the client runs in a deterministic OFFLINE
fallback so the app still demonstrates end-to-end without network access.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

log = logging.getLogger("crm.llm")


class LLMClient:
    def __init__(self) -> None:
        s = get_settings()
        self._settings = s
        self._offline = not s.llm_configured
        if self._offline:
            self._client = None
            log.warning("LLM_API_KEY not set — LLMClient running in OFFLINE fallback mode.")
        else:
            self._client = AsyncOpenAI(
                base_url=s.llm_base_url or None,
                api_key=s.llm_api_key,
                timeout=s.llm_timeout_seconds,
                max_retries=0,  # tenacity handles retries below
            )

    @property
    def offline(self) -> bool:
        return self._offline

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = 900,
    ) -> str:
        if self._offline:
            return self._offline_reply(messages, response_format)

        s = self._settings
        model = model or s.llm_model_chat

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(s.llm_max_retries + 1),
                # 20s max so a Groq 429 (TPM resets each minute) clears next attempt.
                wait=wait_exponential(min=0.5, max=20),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            ):
                with attempt:
                    kwargs: dict[str, Any] = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    }
                    if response_format is not None:
                        kwargs["response_format"] = response_format
                    resp = await self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            # Retries are exhausted (bad key, network down, Groq 429/5xx). Degrade
            # instead of raising, so the rep's interaction is still captured rather
            # than dying as a 500 and losing their note.
            #
            # Return the callers' own "nothing came back" sentinel rather than the
            # keyless placeholder prose: json_chat turns "{}" into {} and backfills
            # from heuristics, and the responder turns "" into its deterministic
            # confirmation. Handing back the OFFLINE text here would instead be
            # shown to the rep verbatim — telling them to set a key they have set.
            log.warning("llm_call_failed model=%s err=%s — degrading", model, exc)
            return "{}" if response_format is not None else ""

        return resp.choices[0].message.content or ""

    async def json_chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Chat call constrained to a JSON object, parsed to a dict."""
        text = await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            log.warning("json_parse_failed raw=%s", text[:300])
            # Best-effort: pull the first {...} block out of the response.
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            return {}

    # ── Offline deterministic fallback (no network / no key) ──────────────
    def _offline_reply(
        self, messages: list[dict[str, Any]], response_format: dict[str, Any] | None
    ) -> str:
        """A tiny rule-based stand-in so the demo works without a Groq key.

        For JSON requests it returns an empty object (callers merge with their
        own heuristics); for prose it echoes a friendly confirmation.
        """
        if response_format is not None:
            return "{}"
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return (
            "✅ Done. (Offline mode — set LLM_API_KEY with a Groq token to enable "
            f"the gemma2-9b-it model.) You said: {user[:160]}"
        )


_client_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = LLMClient()
    return _client_singleton
