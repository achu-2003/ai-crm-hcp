"""Create and migrate the database schema.

`init_db()` runs on startup: it creates the tables (idempotent) and brings an
older database forward with any columns added since it was created.

The app ships with NO demo data — it starts empty and you add your own HCPs from
the UI.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import inspect, text

from app.db.session import engine
from app.models import Base

log = logging.getLogger("crm.seed")


# Columns added after the first release. `create_all` only creates missing
# *tables*, so an existing crm.db / Postgres volume would keep the old shape —
# these ALTERs bring it forward. Both SQLite and Postgres accept
# `ALTER TABLE ... ADD COLUMN ... DEFAULT ...`, and each runs at most once
# because we diff against the live column list first.
_ADDED_COLUMNS: dict[str, str] = {
    "attendees": "JSON DEFAULT '[]'",
    "materials_shared": "JSON DEFAULT '[]'",
    "topics_discussed": "TEXT DEFAULT ''",
    "outcomes": "TEXT DEFAULT ''",
    "follow_up_actions": "TEXT DEFAULT ''",
    "consent_obtained": "BOOLEAN DEFAULT 0",
}


def _existing_columns(sync_conn, table: str) -> set[str]:
    inspector = inspect(sync_conn)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


async def _migrate(conn) -> None:
    """Idempotently add any Interaction column the live DB is missing."""
    present = await conn.run_sync(_existing_columns, "interactions")
    if not present:  # fresh DB — create_all already made the full table
        return
    is_sqlite = conn.dialect.name == "sqlite"
    for column, ddl in _ADDED_COLUMNS.items():
        if column in present:
            continue
        if not is_sqlite:
            # Postgres has no implicit int→bool cast for the DEFAULT literal.
            ddl = ddl.replace("DEFAULT 0", "DEFAULT FALSE")
        await conn.execute(
            text(f"ALTER TABLE interactions ADD COLUMN {column} {ddl}")
        )
        log.info("migrated: added interactions.%s", column)


async def init_db() -> None:
    """Create the tables, then migrate any older database forward."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _migrate(conn)


if __name__ == "__main__":
    asyncio.run(init_db())
