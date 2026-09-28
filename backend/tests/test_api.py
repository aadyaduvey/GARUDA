import csv
import io
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.build_index import build
from app.seed import ANOMALY_DAY, N_DAYS, seed

START = date(2026, 1, 5)
SPIKE_DAY = date.fromordinal(START.toordinal() + ANOMALY_DAY - 1)


@pytest.fixture
def client(engine: Engine, api: TestClient) -> TestClient:
    seed(engine, start=START)
    build(engine)
    return api


def route_id(client: TestClient, label: str) -> int:
    return next(r["id"] for r in client.get("/api/routes").json() if r["label"] == label)


def test_routes_listed_by_weight(client: TestClient) -> None:
    routes = client.get("/api/routes").json()
    assert len(routes) == 10
    assert routes[0]["label"] == "DEL-BOM"


def test_national_series(client: TestClient) -> None:
    body = client.get("/api/index/national").json()
    assert len(body["series"]) == N_DAYS
    assert body["latest"] == body["series"][-1]
    assert body["base_period"] == {"start": "2026-01-05", "end": "2026-01-11"}


def test_route_index_with_carriers(client: TestClient) -> None:
    body = client.get(f"/api/index/route/{route_id(client, 'DEL-BOM')}").json()
    assert len(body["series"]) == N_DAYS
    assert [c["code"] for c in body["carriers"]] == ["6E", "AI", "QP"]
    spike = next(p for p in body["series"] if p["period"] == SPIKE_DAY.isoformat())
    assert spike["anomaly_flag"] is True


def test_unknown_route_is_404(client: TestClient) -> None:
    assert client.get("/api/index/route/999").status_code == 404
    assert client.get("/api/yield-curve/999").status_code == 404


def test_fares_filters(client: TestClient) -> None:
    rid = route_id(client, "DEL-BOM")
    fares = client.get("/api/fares", params={"route_id": rid, "advance_days": 1, "limit": 5000}).json()
    assert len(fares) == N_DAYS * 3 * 2  # days x airlines x days of week
    assert {f["route"] for f in fares} == {"DEL-BOM"} and {f["advance_days"] for f in fares} == {1}

    one_day = client.get("/api/fares", params={"airline": "qp", "start": "2026-01-06", "end": "2026-01-06", "limit": 5000}).json()
    assert len(one_day) == 10 * 4 * 2  # routes x windows x days of week
    assert {f["airline_code"] for f in one_day} == {"QP"}

    assert len(client.get("/api/fares", params={"limit": 7}).json()) == 7


def test_anomalies_only_the_planted_spike(client: TestClient) -> None:
    anomalies = client.get("/api/anomalies").json()
    assert len(anomalies) == 1
    a = anomalies[0]
    assert (a["route"], a["period"], a["severity"]) == ("DEL-BOM", SPIKE_DAY.isoformat(), "high")
    assert a["z_score"] > 2 and a["rise_pct"] >= 5


def test_yield_curve(client: TestClient) -> None:
    body = client.get(f"/api/yield-curve/{route_id(client, 'DEL-BOM')}").json()
    assert len(body["series"]) == N_DAYS * 4
    assert body["premium_1d_vs_30d"] > 1.5


def read_csv(client: TestClient, **params: str) -> list[dict]:
    response = client.get("/api/export/cpi", params=params)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    return list(csv.DictReader(io.StringIO(response.text)))


def test_export_cpi_csv(client: TestClient) -> None:
    rows = read_csv(client)
    assert list(rows[0]) == ["route", "period", "index_value", "weight", "base_period"]
    assert len(rows) == N_DAYS * 11  # 10 routes + national per period
    assert {r["base_period"] for r in rows} == {"2026-01-05/2026-01-11"}
    first_day = [r for r in rows if r["period"] == "2026-01-05"]
    assert first_day[0]["route"] == "DEL-BOM" and first_day[-1]["route"] == "NATIONAL"


def test_export_filters_and_empty_range(client: TestClient) -> None:
    assert len(read_csv(client, start="2026-01-06", end="2026-01-07")) == 2 * 11
    assert read_csv(client, start="2030-01-01", end="2030-01-31") == []  # header only
    assert client.get("/api/export/cpi", params={"start": "2026-01-07", "end": "2026-01-06"}).status_code == 422


def test_cors_allows_dashboard_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:5174"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"
