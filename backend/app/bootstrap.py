"""Make both databases demo-ready without wiping anything. Safe to run on every start:

  uv run python -m app.bootstrap

- demo: create tables, seed synthetic fares if empty, build the index if missing;
- live: create tables, add any missing routes/airlines; build the index if fares exist
  but it is missing. Live fares only ever come from the scrapers.
Both: route weights and airline market shares are refreshed to the current values in app/seed.py.
"""
from sqlalchemy import Engine
from sqlmodel import Session, func, select

from app.build_index import build
from app.db import engine as default_engine, init_db, live_engine as default_live_engine
from app.models import Fare, IndexValue, Route
from app.seed import add_reference_data, seed


def _count(eng: Engine, model) -> int:
    with Session(eng) as session:
        return session.exec(select(func.count()).select_from(model)).one()


def refresh_reference_data(eng: Engine) -> None:
    """Add new airlines/routes and current DGCA shares to an existing database."""
    with Session(eng) as session:
        add_reference_data(session)
        session.commit()


def bootstrap(eng: Engine = default_engine) -> str:
    init_db(eng)
    if _count(eng, Route):
        refresh_reference_data(eng)
    fares, indexed = _count(eng, Fare), _count(eng, IndexValue)
    if fares == 0:
        seed(eng)
        build(eng)
        return "empty database: seeded synthetic fares and built the index"
    if indexed == 0:
        build(eng)
        return f"{fares} fares found: built the index"
    return f"{fares} fares and {indexed} index values found: nothing to do"


def bootstrap_live(eng: Engine = default_live_engine) -> str:
    init_db(eng)
    refresh_reference_data(eng)
    fares, indexed = _count(eng, Fare), _count(eng, IndexValue)
    if fares == 0:
        return "no live fares yet: run `pnpm scrape`, or leave `pnpm start` running for the daily collection"
    if indexed == 0:
        build(eng)
        return f"{fares} live fares found: built the index"
    return f"{fares} live fares and {indexed} index values found: nothing to do"


if __name__ == "__main__":
    from app import official

    print(f"bootstrap demo: {bootstrap()}")
    print(f"bootstrap live: {bootstrap_live()}")
    print(official.refresh())
