from datetime import date

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, func, select

from app.models import Airline, Fare, Route
from app.seed import add_reference_data, seed


def mean_fare(session: Session, advance_days: int) -> float:
    return session.exec(select(func.avg(Fare.amount)).where(Fare.advance_days == advance_days)).one()


def test_seed_row_counts(engine: Engine) -> None:
    counts = seed(engine, start=date(2026, 1, 5))
    # 14 days x 10 routes x 3 synthetic airlines x 4 advance windows x 2 days of week;
    # SpiceJet is listed (4 airlines) but live-only, so it gets no synthetic fares.
    assert counts == {"route": 10, "airline": 4, "fare": 3360, "index_value": 0}


def test_reference_data_refresh_is_idempotent_and_updates_shares(engine: Engine) -> None:
    seed(engine, start=date(2026, 1, 5))
    with Session(engine) as session:
        indigo = session.exec(select(Airline).where(Airline.code == "6E")).one()
        indigo.market_share = 0.5  # stale value from an older release
        session.commit()
    for _ in range(2):
        with Session(engine) as session:
            add_reference_data(session)
            session.commit()
    with Session(engine) as session:
        assert session.exec(select(func.count()).select_from(Airline)).one() == 4
        assert session.exec(select(func.count()).select_from(Route)).one() == 10
        assert session.exec(select(Airline.market_share).where(Airline.code == "6E")).one() == 0.650


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
