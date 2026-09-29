"""SpiceJet parsing, the official MoSPI benchmark, and --watch timing. No network."""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app import official
from app.build_index import build
from app.scraper import scheduler, spicejet
from app.scraper.base import collection_plan
from app.seed import seed

TODAY = date(2026, 9, 29)  # a Tuesday


# --- SpiceJet -------------------------------------------------------------------


def test_spicejet_calendar_total_includes_taxes_and_skips_no_flight_days() -> None:
    payload = {
        "data": {
            "lowFareDateMarkets": [
                {"departureDate": "2026-10-13T00:00:00", "lowestFareAmount": {"fareAmount": 4900, "taxesAndFeesAmount": 1547}},
                {"departureDate": "2026-10-14T00:00:00", "lowestFareAmount": None},
                {"departureDate": "2026-10-15T00:00:00", "lowestFareAmount": {"fareAmount": 0, "taxesAndFeesAmount": 0}},
            ]
        }
    }
    assert spicejet.parse_low_fares(payload) == {date(2026, 10, 13): 6447.0}
    assert spicejet.parse_low_fares({"data": None}) == {}


def test_spicejet_calendars_cover_every_planned_departure() -> None:
    covered = {
        centre + timedelta(days=d)
        for centre in spicejet.calendar_centres(TODAY)
        for d in range(-spicejet.CALENDAR_HALF_WIDTH, spicejet.CALENDAR_HALF_WIDTH + 1)
    }
    assert {departure for _, _, departure in collection_plan(TODAY)} <= covered


def test_spicejet_cheapest_same_airports_uses_adult_total() -> None:
    payload = {
        "data": {
            "faresAvailable": {
                "k1": {"passengerFares": [{"passengerType": "ADT", "fareAmount": 6447}]},
                "k2": {"passengerFares": [{"passengerType": "ADT", "fareAmount": 5874}]},
                "k3": {"passengerFares": [{"passengerType": "CHD", "fareAmount": 100}]},
            },
            "trips": [
                {
                    "journeysAvailable": [
                        {"designator": {"origin": "DEL", "destination": "BOM"}, "fares": {"k1": {}, "k3": {}}},
                        {"designator": {"origin": "DEL", "destination": "NMI"}, "fares": {"k2": {}}},
                    ]
                }
            ],
        }
    }
    assert spicejet.cheapest_same_airports(payload, "DEL", "BOM") == 6447.0
    assert spicejet.cheapest_same_airports(payload, "DEL", "BLR") is None


# --- Official MoSPI benchmark ------------------------------------------------------


def test_official_rows_parse_to_sorted_months() -> None:
    rows = [
        {"year": "2026", "month": "August", "index": "135.49", "inflation": "20.85"},
        {"year": "2025", "month": "January", "index": "115.05", "inflation": None},
        {"year": "2026", "month": "September", "index": ""},  # not yet published
    ]
    assert official.parse_rows(rows) == [
        {"month": "2025-01", "index": 115.05, "inflation": None},
        {"month": "2026-08", "index": 135.49, "inflation": 20.85},
    ]


OFFICIAL = [{"month": "2026-07", "index": 125.46, "inflation": None}, {"month": "2026-08", "index": 135.49, "inflation": None}]


def test_link_needs_enough_days_in_a_published_month() -> None:
    september = [(date(2026, 9, d), 100.0) for d in range(1, 29)]
    assert official.link_to_official(september, OFFICIAL) is None  # September not published yet
    few_august = [(date(2026, 8, d), 100.0) for d in range(25, 31)]  # 6 days < LINK_MIN_DAYS
    assert official.link_to_official(few_august, OFFICIAL) is None
    assert official.link_to_official([], OFFICIAL) is None


def test_link_rescales_garuda_onto_the_official_2024_base() -> None:
    august = [(date(2026, 8, d), 100.0 if d % 2 else 121.0) for d in range(18, 32)]  # 14 days
    link = official.link_to_official(august + [(date(2026, 9, 1), 110.0)], OFFICIAL)
    assert link is not None and link.month == "2026-08" and link.garuda_days == 14
    assert link.factor == pytest.approx(135.49 / 110.0)  # geometric mean of 100 and 121 = 110
    assert link.latest_period == date(2026, 9, 1)
    assert link.latest_value == pytest.approx(135.49)


def test_official_endpoint_serves_saved_copy(api: TestClient, engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seed(engine, start=date(2026, 1, 5))
    build(engine)
    cache = tmp_path / "cpi_airfare.json"
    monkeypatch.setattr(official, "CACHE_FILE", cache)
    assert api.get("/api/official/cpi-airfare").json()["available"] is False

    cache.write_text(json.dumps({"source": {"name": "MoSPI eSankhyiki, CPI (base 2024)"}, "fetched_at": "2026-09-29T10:00:00+00:00", "series": OFFICIAL}))
    body = api.get("/api/official/cpi-airfare").json()
    assert body["available"] is True and body["code"] == "07.3.3.1.2.01"
    assert [p["month"] for p in body["series"]] == ["2026-07", "2026-08"]
    assert body["link"] is None  # demo data is January 2026: no published month overlaps


def test_refresh_keeps_saved_copy_when_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cpi_airfare.json"
    cache.write_text(json.dumps({"fetched_at": "2020-01-01T00:00:00+00:00", "series": OFFICIAL}))

    def offline(*_a, **_k):
        raise OSError("no network")

    monkeypatch.setattr(official, "fetch", offline)
    assert "refresh failed" in official.refresh(cache)
    assert json.loads(cache.read_text())["series"] == OFFICIAL


# --- --watch timing ----------------------------------------------------------------


def test_watch_collects_on_start_unless_fares_are_minutes_old() -> None:
    now = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)
    assert scheduler.start_up_batch_due(None, now)
    assert scheduler.start_up_batch_due(now - timedelta(hours=2), now)
    assert not scheduler.start_up_batch_due(now - timedelta(minutes=5), now)
