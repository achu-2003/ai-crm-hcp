"""Create the database schema, and optionally seed sample demo data.

`init_db()` always runs on startup: it creates the tables (idempotent) and,
only when SEED_DEMO_DATA=true, inserts a few realistic HCPs + sample
interactions so the app has something to show immediately. With the flag off
(the default) the app starts completely clean — add your own HCPs from the UI.

Runnable standalone to force-seed the demo data: `python -m app.seed`.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta, datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.db.session import engine, session_scope
from app.models import Base, HCP, Interaction

_HCPS = [
    dict(name="Dr. Ananya Mehta", specialty="Cardiology", institution="Apollo Hospitals",
         tier="A", preferred_products=["Cardizem", "Brilinta"], email="a.mehta@apollo.example", city="Mumbai"),
    dict(name="Dr. Rajiv Rao", specialty="Endocrinology", institution="Fortis Healthcare",
         tier="A", preferred_products=["Jardiance", "Ozempic"], email="r.rao@fortis.example", city="Bengaluru"),
    dict(name="Dr. Sara Kapoor", specialty="Oncology", institution="Tata Memorial Centre",
         tier="B", preferred_products=["Keytruda"], email="s.kapoor@tmc.example", city="Mumbai"),
    dict(name="Dr. Vivek Nair", specialty="Pulmonology", institution="AIIMS",
         tier="B", preferred_products=["Trelegy", "Symbicort"], email="v.nair@aiims.example", city="Delhi"),
    dict(name="Dr. Priya Sharma", specialty="Neurology", institution="Manipal Hospitals",
         tier="C", preferred_products=["Aimovig"], email="p.sharma@manipal.example", city="Pune"),
    dict(name="Dr. Imran Sheikh", specialty="Rheumatology", institution="Max Healthcare",
         tier="B", preferred_products=["Humira", "Rinvoq"], email="i.sheikh@max.example", city="Delhi"),
]


async def init_db(force_demo: bool = False) -> None:
    """Create tables always; seed demo data only when enabled."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if not (force_demo or get_settings().seed_demo_data):
        return

    async with session_scope() as s:
        existing = (await s.execute(select(HCP).limit(1))).scalar_one_or_none()
        if existing is not None:
            return

        hcps = [HCP(**data) for data in _HCPS]
        s.add_all(hcps)
        await s.flush()

        now = datetime.now(timezone.utc)
        mehta = hcps[0]
        s.add_all([
            Interaction(
                hcp_id=mehta.id, rep_name="Field Rep", interaction_type="visit",
                interaction_date=now - timedelta(days=21), channel="in-person",
                products_discussed=["Cardizem"], samples_dropped=["Cardizem x5"],
                sentiment="positive", key_topics=["dosing", "formulary access"],
                summary="In-person visit with Dr. Mehta; discussed Cardizem dosing and left 5 samples. Receptive.",
                raw_notes="Met Dr Mehta at Apollo, talked Cardizem dosing, left 5 samples, very receptive, wants follow up.",
                follow_up_needed=True, source="form",
            ),
            Interaction(
                hcp_id=hcps[1].id, rep_name="Field Rep", interaction_type="call",
                interaction_date=now - timedelta(days=7), channel="phone",
                products_discussed=["Jardiance"], samples_dropped=[],
                sentiment="neutral", key_topics=["reimbursement"],
                summary="Phone call with Dr. Rao on Jardiance reimbursement; neutral, needs more data.",
                raw_notes="Called Dr Rao about Jardiance reimbursement, neutral, asked for more outcome data.",
                follow_up_needed=True, source="form",
            ),
        ])


if __name__ == "__main__":
    # Running this module directly always seeds the demo data.
    asyncio.run(init_db(force_demo=True))
