import csv
import io
import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.build_index import build
from app.export_snapshot import export
from app.seed import N_DAYS, seed


def test_export_writes_every_file_the_dashboard_reads(engine: Engine, api: TestClient, tmp_path: Path) -> None:
    seed(engine, start=date(2026, 1, 5))
    build(engine)
    counts = export(tmp_path, api)  # the conftest override serves the same DB for both datasets

    # routes, national, anomalies, status, cpi.csv + a route and a yield file per route
    assert counts == {"demo": 5 + 2 * 10, "live": 5 + 2 * 10}
    demo = tmp_path / "demo"
    assert len(json.loads((demo / "national.json").read_text())["series"]) == N_DAYS
    assert json.loads((demo / "route-1.json").read_text())["route"]["id"] == 1
    rows = list(csv.DictReader(io.StringIO((demo / "cpi.csv").read_text())))
    assert len(rows) == N_DAYS * 11
    assert "generated_at" in json.loads((tmp_path / "meta.json").read_text())


def test_export_replaces_an_old_snapshot(engine: Engine, api: TestClient, tmp_path: Path) -> None:
    seed(engine, start=date(2026, 1, 5))
    build(engine)
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "stale.json").write_text("{}")
    export(tmp_path, api)
    assert not (tmp_path / "demo" / "stale.json").exists()
