"""SQLite engines + session.

Two databases with the same schema:
- demo: synthetic seed only, so the demo's numbers are stable and clean;
- live: real scraped fares only, building a genuine (Akasa-only for now) index day by day.
"""
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from fastapi import Query
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers tables on SQLModel.metadata)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCRAPER_STATUS_FILE = DATA_DIR / "scraper_status.json"  # written by each scrape batch, read by /api/status
DB_URL = os.environ.get("GARUDA_DB_URL", f"sqlite:///{(DATA_DIR / 'garuda.db').as_posix()}")
LIVE_DB_URL = os.environ.get("GARUDA_LIVE_DB_URL", f"sqlite:///{(DATA_DIR / 'garuda_live.db').as_posix()}")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
live_engine = create_engine(LIVE_DB_URL, connect_args={"check_same_thread": False})

Dataset = Literal["demo", "live"]
ENGINES: dict[str, Engine] = {"demo": engine, "live": live_engine}


def init_db(eng: Engine = engine) -> None:
    SQLModel.metadata.create_all(eng)


def reset_db(eng: Engine = engine) -> None:
    SQLModel.metadata.drop_all(eng)
    SQLModel.metadata.create_all(eng)


def get_session(
    dataset: Dataset = Query("demo", description="demo = synthetic seed; live = real scraped fares"),
) -> Iterator[Session]:
    with Session(ENGINES[dataset]) as session:
        yield session
