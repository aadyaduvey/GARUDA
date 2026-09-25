"""Demo and live databases are separate: the dashboard switches between them with ?dataset=."""
from collections.abc import Iterator
from datetime import date, datetime, timezone

import pytest
from fastapi import Query
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, func, select

from app.bootstrap import bootstrap_live
from app.build_index import build
from app.db import Dataset, get_session
from app.main import app
from app.models import Fare, Route
from app.pipeline.ingest import ingest
from app.scraper.base import FareRow
from app.seed import seed


@pytest.fixture
def live() -> Iterator[Engine]:
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield eng
    eng.dispose()


@pytest.fixture
def client(engine: Engine, live: Engine) -> Iterator[TestClient]:
    seed(engine, start=date(2026, 1, 5))
    build(engine)
    bootstrap_live(live)
    engines = {"demo": engine, "live": live}

    def session_override(dataset: Dataset = Query("demo")) -> Iterator[Session]:
        with Session(engines[dataset]) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_bootstrap_live_creates_reference_data_but_no_fares(live: Engine) -> None:
    assert "no live fares yet" in bootstrap_live(live)
    with Session(live) as session:
        assert session.exec(select(func.count()).select_from(Route)).one() == 10
        assert session.exec(select(func.count()).select_from(Fare)).one() == 0
    assert "no live fares yet" in bootstrap_live(live)  # idempotent: routes not duplicated
    with Session(live) as session:
        assert session.exec(select(func.count()).select_from(Route)).one() == 10


def test_dataset_param_switches_database(client: TestClient) -> None:
    assert len(client.get("/api/index/national").json()["series"]) == 14  # default = demo
    assert len(client.get("/api/index/national", params={"dataset": "demo"}).json()["series"]) == 14
    assert client.get("/api/index/national", params={"dataset": "live"}).json()["series"] == []
    assert len(client.get("/api/routes", params={"dataset": "live"}).json()) == 10
    status = client.get("/api/status", params={"dataset": "live"}).json()
    assert (status["dataset"], status["days_collected"], status["fares_by_source"]) == ("live", 0, {})
    assert client.get("/api/index/national", params={"dataset": "bogus"}).status_code == 422


def test_live_fares_build_a_live_index_and_leave_demo_untouched(client: TestClient, live: Engine) -> None:
    demo_before = client.get("/api/index/national").json()
    ts = datetime(2026, 9, 25, 0, 30, tzinfo=timezone.utc)
    rows = [FareRow("QP", "DEL", "BOM", 6880.0, w, d, date(2026, 10, 6), "economy", ts, "akasa_lowfare") for w in (1, 7, 14, 30) for d in ("TUE", "SAT")]
    with Session(live) as session:
        ingest(session, rows)
    assert "built the index" in bootstrap_live(live)

    live_index = client.get("/api/index/national", params={"dataset": "live"}).json()
    assert [p["national_index"] for p in live_index["series"]] == [pytest.approx(100.0)]  # day 1 of the base week
    assert client.get("/api/status", params={"dataset": "live"}).json()["days_collected"] == 1
    assert client.get("/api/index/national").json() == demo_before
