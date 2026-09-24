from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Empty in-memory SQLite DB, isolated per test. Never touches data/garuda.db."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield eng
    eng.dispose()
