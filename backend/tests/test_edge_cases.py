"""Edge cases from the QA checklist: missing data must degrade gracefully, never crash or mis-index."""
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlmodel import Session, delete, func, select

from app import db
from app.bootstrap import bootstrap
from app.build_index import BASE_DAYS, build, load_fares
from app.db import init_db
from app.models import IST, Airline, Fare, Route
from app.pipeline.clean import drop_outliers
from app.pipeline.impute import carry_forward
from app.seed import N_DAYS, seed

START = date(2026, 1, 5)


def route_id(engine: Engine, label: str) -> int:
    origin, destination = label.split("-")
    with Session(engine) as session:
        return session.exec(select(Route.id).where(Route.origin == origin, Route.destination == destination)).one()


def delete_fares(engine: Engine, *conditions) -> None:
    with Session(engine) as session:
        session.exec(delete(Fare).where(*conditions))
        session.commit()


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=IST)
    return start, start + timedelta(days=1)


@pytest.fixture
def seeded(engine: Engine) -> Engine:
    seed(engine, start=START)
    return engine


def test_route_with_zero_fares(seeded: Engine, api: TestClient) -> None:
    rid = route_id(seeded, "BLR-PNQ")
    delete_fares(seeded, Fare.route_id == rid)
    routes, national = build(seeded)

    assert rid not in set(routes["route_id"])
    assert len(national) == N_DAYS  # national index renormalises over the 9 remaining routes
    assert national["national_index"].head(BASE_DAYS).mean() == pytest.approx(100, abs=1)

    body = api.get(f"/api/index/route/{rid}").json()
    assert body["series"] == [] and body["carriers"] == []
    assert api.get(f"/api/yield-curve/{rid}").json()["premium_1d_vs_30d"] is None
    assert len(api.get("/api/export/cpi").text.strip().splitlines()) == 1 + N_DAYS * 10  # header + 9 routes + national


def test_single_airline_route(seeded: Engine, api: TestClient) -> None:
    rid = route_id(seeded, "DEL-BOM")
    with Session(seeded) as session:
        akasa = session.exec(select(Airline.id).where(Airline.code == "QP")).one()
    delete_fares(seeded, Fare.route_id == rid, Fare.airline_id != akasa)
    routes, _ = build(seeded)

    del_bom = routes[routes["route_id"] == rid]
    assert len(del_bom) == N_DAYS
    assert del_bom["jevons_index"].head(BASE_DAYS).mean() == pytest.approx(100, abs=1)
    assert [c["code"] for c in api.get(f"/api/index/route/{rid}").json()["carriers"]] == ["QP"]


def test_day_with_no_fares_is_carried_forward_and_flagged(seeded: Engine) -> None:
    rid = route_id(seeded, "DEL-MAA")
    gap, before = START + timedelta(days=4), START + timedelta(days=3)
    lo, hi = day_bounds(gap)
    delete_fares(seeded, Fare.route_id == rid, Fare.scrape_ts >= lo, Fare.scrape_ts < hi)

    with Session(seeded) as session:
        fares = load_fares(session)
    quotes = carry_forward(drop_outliers(fares), sorted(fares["period"].unique()))
    gap_quotes = quotes[(quotes["route_id"] == rid) & (quotes["period"] == gap)]
    assert len(gap_quotes) == 3 * 4 * 2 and gap_quotes["imputed"].all()

    routes, _ = build(seeded)
    series = routes[routes["route_id"] == rid].set_index("period")["jevons_index"]
    assert series[gap] == pytest.approx(series[before])  # all quotes carried forward = unchanged index


def test_zero_and_extreme_fares_are_filtered_before_jevons(seeded: Engine) -> None:
    before = build(seeded)[1]["national_index"].tolist()
    rid = route_id(seeded, "DEL-BOM")
    ts = datetime.combine(START + timedelta(days=13), time(7, 0), tzinfo=IST)
    with Session(seeded) as session:
        session.add_all(
            Fare(route_id=rid, airline_id=1, amount=amount, advance_days=1, dep_dow="TUE", scrape_ts=ts, source="bad")
            for amount in (0, 120, 99_999)
        )
        session.commit()
    assert build(seeded)[1]["national_index"].tolist() == pytest.approx(before)


def test_empty_database(engine: Engine, api: TestClient) -> None:
    init_db(engine)
    with pytest.raises(ValueError, match="no fares"):
        build(engine)
    assert api.get("/api/index/national").json() == {"base_period": None, "latest": None, "series": []}
    assert api.get("/api/anomalies").json() == []
    assert api.get("/api/routes").json() == []
    assert api.get("/api/export/cpi").text.strip() == "route,period,index_value,weight,base_period"
    status = api.get("/api/status").json()
    assert status["fares_by_source"] == {} and status["latest_period"] is None


def test_bootstrap_seeds_an_empty_db_once(engine: Engine) -> None:
    assert "seeded" in bootstrap(engine)
    assert "nothing to do" in bootstrap(engine)
    with Session(engine) as session:
        assert session.exec(select(func.count()).select_from(Fare)).one() == 3360


def test_status_reports_last_scraper_run(seeded: Engine, api: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    status_file = tmp_path / "scraper_status.json"
    monkeypatch.setattr(db, "SCRAPER_STATUS_FILE", status_file)
    build(seeded)
    assert api.get("/api/status").json()["last_run"] is None  # no batch has run yet

    run = {
        "run_at": "2026-01-18T00:45:00+00:00",
        "mode": "live",
        "index_rebuilt": True,
        "sources": [
            {"airline": "QP", "name": "Akasa Air", "status": "ok", "rows": 8, "inserted": 8, "duplicates": 0, "rejected": {}, "error": None},
            {"airline": "6E", "name": "IndiGo", "status": "unavailable", "rows": 0, "inserted": 0, "duplicates": 0, "rejected": {}, "error": "robots.txt"},
        ],
    }
    status_file.write_text(json.dumps(run))
    live_ts = datetime(2026, 1, 18, 0, 45, tzinfo=timezone.utc)
    with Session(seeded) as session:
        session.add(Fare(route_id=1, airline_id=3, amount=6880, advance_days=1, dep_dow="SAT", scrape_ts=live_ts, source="akasa_lowfare"))
        session.commit()

    body = api.get("/api/status").json()
    assert body["latest_period"] == "2026-01-18"
    assert body["fares_by_source"] == {"synthetic": 3360, "akasa_lowfare": 1}
    assert body["last_live_fare_at"].startswith("2026-01-18T00:45")
    assert [s["status"] for s in body["last_run"]["sources"]] == ["ok", "unavailable"]
