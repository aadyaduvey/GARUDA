"""SQLite engine + session."""
import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers tables on SQLModel.metadata)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_URL = os.environ.get("GARUDA_DB_URL", f"sqlite:///{(DATA_DIR / 'garuda.db').as_posix()}")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})


def init_db(eng: Engine = engine) -> None:
    SQLModel.metadata.create_all(eng)


def reset_db(eng: Engine = engine) -> None:
    SQLModel.metadata.drop_all(eng)
    SQLModel.metadata.create_all(eng)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
