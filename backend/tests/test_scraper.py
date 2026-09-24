import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, func, select

from app.models import Fare, IndexValue
from app.pipeline.ingest import ingest
from app.scraper import scheduler
from app.scraper.akasa import parse_low_fares
from app.scraper.base import FareRow, Scraper, ScraperError, collection_plan, select_quotes
from app.seed import seed

TODAY = date(2026, 9, 25)  # a Friday
TS = datetime(2026, 9, 25, 0, 30, tzinfo=timezone.utc)


def row(amount: float = 6880.0, advance_days: int = 1, dep_dow: str = "SAT", origin: str = "DEL", destination: str = "BOM", airline: str = "QP") -> FareRow:
    return FareRow(airline, origin, destination, amount, advance_days, dep_dow, date(2026, 9, 26), "economy", TS, "test_source")


# --- Collection plan & parsing (pure) ---------------------------------------


def test_collection_plan_prices_the_next_tuesday_and_saturday_at_least_window_days_ahead() -> None:
    plan = collection_plan(TODAY)
    assert len(plan) == 8
    for window, dow, dep in plan:
        assert dep.weekday() == {"TUE": 1, "SAT": 5}[dow]
        assert window <= (dep - TODAY).days < window + 7
    assert (1, "SAT", date(2026, 9, 26)) in plan and (30, "TUE", date(2026, 10, 27)) in plan


def test_parse_low_fares_skips_no_flight_and_sold_out_days() -> None:
    payload = {
        "data": {
            "lowFares": [
                {"date": "2026-09-26T00:00:00", "price": 6880.0, "noFlights": False, "soldOut": False},
                {"date": "2026-09-27T00:00:00", "price": 0, "noFlights": True, "soldOut": False},
                {"date": "2026-09-28T00:00:00", "price": 7100.0, "noFlights": False, "soldOut": True},
            ]
        }
    }
    assert parse_low_fares(payload) == {date(2026, 9, 26): 6880.0}
    assert parse_low_fares({"data": None}) == {}


def test_select_quotes_picks_plan_dates_from_calendar() -> None:
    calendar = {dep: 5000.0 + i for i, (_, _, dep) in enumerate(collection_plan(TODAY))}
    del calendar[date(2026, 9, 26)]  # 1-day Saturday not on sale
    quotes = select_quotes(calendar, today=TODAY, airline="QP", origin="DEL", destination="BOM", scrape_ts=TS, source="s")
    assert len(quotes) == 7
    assert all(q.dep_date in calendar and q.amount == calendar[q.dep_date] for q in quotes)


def test_fare_row_json_round_trip() -> None:
    assert FareRow.from_json(row().to_json()) == row()


# --- Ingest ------------------------------------------------------------------


@pytest.fixture
def seeded(engine: Engine) -> Engine:
    seed(engine, start=date(2026, 9, 12))
    return engine


def fare_count(engine: Engine, source: str) -> int:
    with Session(engine) as session:
        return session.exec(select(func.count()).select_from(Fare).where(Fare.source == source)).one()


def test_ingest_inserts_valid_rows_and_rejects_bad_ones(seeded: Engine) -> None:
    rows = [row(), row(advance_days=7), row(origin="DEL", destination="XYZ"), row(advance_days=3), row(amount=0), row(airline="ZZ")]
    with Session(seeded) as session:
        result = ingest(session, rows)
    assert result.inserted == 2
    assert sum(result.rejected.values()) == 4
    assert fare_count(seeded, "test_source") == 2


def test_ingest_is_idempotent(seeded: Engine) -> None:
    with Session(seeded) as session:
        ingest(session, [row()])
        again = ingest(session, [row()])
    assert (again.inserted, again.duplicates) == (0, 1)
    assert fare_count(seeded, "test_source") == 1


# --- Batch: failures never crash, dry-run is offline -------------------------


class FakeScraper(Scraper):
    def __init__(self, airline: str, rows: list[FareRow] | None = None, error: Exception | None = None):
        self.airline, self.name, self.source = airline, f"fake-{airline}", f"fake_{airline.lower()}"
        self.rows, self.error, self.calls = rows or [], error, 0

    def scrape(self, routes, today):
        self.calls += 1
        if self.error:
            raise self.error
        return self.rows


def run(seeded: Engine, tmp_path: Path, scrapers: dict, **kw) -> dict:
    return scheduler.run_batch(eng=seeded, scrapers=scrapers, cache_dir=tmp_path / "cache", status_file=tmp_path / "status.json", **kw)


def test_failing_scraper_is_logged_and_batch_continues(seeded: Engine, tmp_path: Path) -> None:
    scrapers = {
        "6E": FakeScraper("6E", error=ScraperError("blocked by anti-bot")),
        "AI": FakeScraper("AI", error=RuntimeError("site layout changed")),
        "QP": FakeScraper("QP", rows=[row(), row(advance_days=7)]),
    }
    report = run(seeded, tmp_path, scrapers)
    by_code = {s["airline"]: s for s in report["sources"]}
    assert by_code["6E"]["status"] == "failed" and "blocked" in by_code["6E"]["error"]
    assert by_code["AI"]["status"] == "failed" and "RuntimeError" in by_code["AI"]["error"]
    assert by_code["QP"]["status"] == "ok" and by_code["QP"]["inserted"] == 2
    assert report["index_rebuilt"] is True
    assert json.loads((tmp_path / "status.json").read_text())["sources"] == report["sources"]
    with Session(seeded) as session:
        assert session.exec(select(func.count()).select_from(IndexValue)).one() > 0


def test_dry_run_uses_cache_and_never_scrapes(seeded: Engine, tmp_path: Path) -> None:
    live = FakeScraper("QP", rows=[row(advance_days=w, dep_dow=d) for w in (1, 7, 14, 30) for d in ("TUE", "SAT")])
    run(seeded, tmp_path, {"QP": live})  # live run caches a 3-row sample
    offline = FakeScraper("QP", error=AssertionError("dry run must not hit the network"))
    offline.source = live.source
    report = run(seeded, tmp_path, {"QP": offline}, dry_run=True)
    assert offline.calls == 0
    assert report["mode"] == "dry_run"
    assert report["sources"][0]["status"] == "ok" and report["sources"][0]["rows"] == scheduler.DRY_RUN_ROWS


def test_dry_run_without_cache_fails_cleanly(seeded: Engine, tmp_path: Path) -> None:
    report = run(seeded, tmp_path, {"QP": FakeScraper("QP")}, dry_run=True)
    assert report["sources"][0]["status"] == "failed"
    assert "no cached sample" in report["sources"][0]["error"]
