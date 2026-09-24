"""Make the DB demo-ready without wiping anything: create tables, seed if empty, build the index if missing.

Safe to run on every start:  uv run python -m app.bootstrap
"""
from sqlalchemy import Engine
from sqlmodel import Session, func, select

from app.build_index import build
from app.db import engine as default_engine, init_db
from app.models import Fare, IndexValue
from app.seed import seed


def bootstrap(eng: Engine = default_engine) -> str:
    init_db(eng)
    with Session(eng) as session:
        fares = session.exec(select(func.count()).select_from(Fare)).one()
        indexed = session.exec(select(func.count()).select_from(IndexValue)).one()
    if fares == 0:
        seed(eng)
        build(eng)
        return "empty database: seeded synthetic fares and built the index"
    if indexed == 0:
        build(eng)
        return f"{fares} fares found: built the index"
    return f"{fares} fares and {indexed} index values found: nothing to do"


if __name__ == "__main__":
    print(f"bootstrap: {bootstrap()}")
