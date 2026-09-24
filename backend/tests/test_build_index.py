from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, func, select

from app.build_index import BASE_DAYS, build
from app.models import IndexValue, Route
from app.seed import ANOMALY_DAY, N_DAYS, seed

START = date(2026, 1, 5)


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    seed(eng, start=START)
    yield eng
    eng.dispose()


def test_writes_route_and_national_rows(engine: Engine) -> None:
    build(engine)
    with Session(engine) as session:
        assert session.exec(select(func.count()).select_from(IndexValue)).one() == N_DAYS * 10 + N_DAYS


def test_base_week_national_index_averages_100(engine: Engine) -> None:
    _, national = build(engine)
    assert national["national_index"].head(BASE_DAYS).mean() == pytest.approx(100, abs=1)


def test_planted_del_bom_spike_is_flagged(engine: Engine) -> None:
    routes, _ = build(engine)
    with Session(engine) as session:
        del_bom = session.exec(select(Route).where(Route.origin == "DEL", Route.destination == "BOM")).one().id
    flagged = routes[routes["anomaly_flag"]]
    spike_day = date.fromordinal(START.toordinal() + ANOMALY_DAY - 1)
    assert ((flagged["route_id"] == del_bom) & (flagged["period"] == spike_day)).any()
