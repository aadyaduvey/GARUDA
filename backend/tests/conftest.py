from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app.db import get_session
from app.main import app


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Empty in-memory SQLite DB, isolated per test. Never touches data/garuda.db."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield eng
    eng.dispose()


@pytest.fixture
def api(engine: Engine) -> Iterator[TestClient]:
    """TestClient whose requests read `engine`. Seed or modify the engine before calling it."""

    def session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    yield TestClient(app)
    app.dependency_overrides.clear()
