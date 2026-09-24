from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, func, select

from app.models import Fare, Route
from app.seed import seed


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield eng
    eng.dispose()


def mean_fare(session: Session, advance_days: int) -> float:
    return session.exec(select(func.avg(Fare.amount)).where(Fare.advance_days == advance_days)).one()


def test_seed_row_counts(engine: Engine) -> None:
    counts = seed(engine, start=date(2026, 1, 5))
    # 14 days x 10 routes x 3 airlines x 4 advance windows x 2 days of week
    assert counts == {"route": 10, "airline": 3, "fare": 3360, "index_value": 0}


def test_one_day_fares_dearer_than_thirty_day(engine: Engine) -> None:
    seed(engine, start=date(2026, 1, 5))
    with Session(engine) as session:
        assert mean_fare(session, 1) > mean_fare(session, 30)
        assert mean_fare(session, 30) < mean_fare(session, 14) < mean_fare(session, 7) < mean_fare(session, 1)


def test_route_weights_sum_to_one_and_fares_within_outlier_bounds(engine: Engine) -> None:
    seed(engine, start=date(2026, 1, 5))
    with Session(engine) as session:
        assert session.exec(select(func.sum(Route.dgca_weight))).one() == pytest.approx(1.0)
        lo, hi = session.exec(select(func.min(Fare.amount), func.max(Fare.amount))).one()
        assert 500 <= lo and hi <= 50_000
