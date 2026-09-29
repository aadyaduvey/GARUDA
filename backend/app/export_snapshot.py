"""Export every response the dashboard needs, for both datasets, as static files.

The published website (`pnpm website`) is the dashboard built in static mode, reading these
files instead of calling the API, so it needs no server and never goes to sleep.

  uv run python -m app.export_snapshot        # writes frontend/public/snapshot/
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.bootstrap import bootstrap, bootstrap_live
from app.main import app

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "snapshot"
DATASETS = ("demo", "live")


def export(out: Path = OUT, client: TestClient | None = None) -> dict[str, int]:
    """Write <out>/<dataset>/*.json + cpi.csv and <out>/meta.json. Returns files written per dataset."""
    client = client or TestClient(app)
    if out.exists():
        shutil.rmtree(out)
    counts = {}
    for dataset in DATASETS:
        folder = out / dataset
        folder.mkdir(parents=True)

        def save(filename: str, path: str) -> str:
            response = client.get(path, params={"dataset": dataset})
            response.raise_for_status()
            (folder / filename).write_text(response.text, encoding="utf-8")
            return response.text

        routes = json.loads(save("routes.json", "/api/routes"))
        save("national.json", "/api/index/national")
        save("anomalies.json", "/api/anomalies")
        save("status.json", "/api/status")
        save("cpi.csv", "/api/export/cpi")
        for route in routes:
            save(f"route-{route['id']}.json", f"/api/index/route/{route['id']}")
            save(f"yield-{route['id']}.json", f"/api/yield-curve/{route['id']}")
        counts[dataset] = len(list(folder.iterdir()))
    (out / "meta.json").write_text(
        json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}), encoding="utf-8"
    )
    return counts


if __name__ == "__main__":
    print(f"bootstrap demo: {bootstrap()}")
    print(f"bootstrap live: {bootstrap_live()}")
    for dataset, n in export().items():
        print(f"{dataset}: {n} files")
    print(f"snapshot written to {OUT}")
