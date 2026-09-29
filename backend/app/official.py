"""Official benchmark: MoSPI's CPI "Airfare" item index (base 2024 = 100), from eSankhyiki.

MoSPI publishes it monthly (All India, rural + urban combined, item 07.3.3.1.2.01) through its
open API, api.mospi.gov.in, the backend of esankhyiki.mospi.gov.in (robots.txt: Allow /).
GARUDA keeps a copy in data/official/cpi_airfare.json, refreshed by the collector and by
`pnpm start`, so the dashboard shows it offline too.

  uv run python -m app.official      # refresh the copy now

Linking. GARUDA's own base is its first collection week. Once GARUDA has at least
LINK_MIN_DAYS days inside a month that MoSPI has published, the series is chain-linked:
    GARUDA(base 2024) = GARUDA(t) x official(m) / geometric mean of GARUDA's days in m
using the latest such month m, which puts GARUDA on MoSPI's 2024 = 100 scale.
"""
import json
import logging
import ssl
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import numpy as np

from app.db import DATA_DIR

log = logging.getLogger("garuda.official")

API_URL = "https://api.mospi.gov.in/api/cpi/getCPIData"
PORTAL_URL = "https://esankhyiki.mospi.gov.in/macroindicators?product=cpi"
QUERY = {"base_year": "2024", "level": "Item", "item_code": 294, "state_code": 1, "sector_code": 3, "series": "Current"}
ITEM = {"name": "Airfare", "code": "07.3.3.1.2.01", "base_year": "2024", "area": "All India, rural + urban"}
FIRST_YEAR = 2025  # the 2024-base series starts in January 2025
CACHE_FILE = DATA_DIR / "official" / "cpi_airfare.json"
MAX_AGE = timedelta(hours=12)
LINK_MIN_DAYS = 7
# api.mospi.gov.in needs TLS legacy renegotiation, which OpenSSL 3 refuses by default (MoSPI's own
# client, mospi-esankhyiki, enables it the same way). Certificates are still fully verified.
OP_LEGACY_SERVER_CONNECT = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)


def tls_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.options |= OP_LEGACY_SERVER_CONNECT
    return ctx


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def parse_rows(rows: Sequence[dict]) -> list[dict]:
    """API rows -> [{month: 'YYYY-MM', index, inflation}] (inflation = % vs same month a year earlier)."""
    out = []
    for r in rows:
        if r.get("index") in (None, ""):
            continue
        month = f"{int(r['year']):04d}-{MONTHS.index(r['month']) + 1:02d}"
        inflation = r.get("inflation")
        out.append({"month": month, "index": float(r["index"]), "inflation": float(inflation) if inflation not in (None, "") else None})
    return sorted(out, key=lambda p: p["month"])


def fetch(client: httpx.Client, today: date) -> list[dict]:
    rows: list[dict] = []
    for year in range(FIRST_YEAR, today.year + 1):
        page, pages = 1, 1
        while page <= pages:
            payload = client.get(API_URL, params={**QUERY, "year": year, "page": page}).raise_for_status().json()
            if not payload.get("statusCode"):
                raise ValueError(f"MoSPI API: {payload.get('msg')}")
            rows += payload.get("data") or []
            pages = (payload.get("meta_data") or {}).get("totalPages") or 1
            page += 1
    series = parse_rows(rows)
    if not series:
        raise ValueError("MoSPI API returned no airfare index values")
    return series


def load(cache: Path = CACHE_FILE) -> dict | None:
    try:
        return json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def refresh(cache: Path = CACHE_FILE, max_age: timedelta = MAX_AGE, force: bool = False) -> str:
    """Re-download the series if the copy is missing or older than `max_age`. Never raises."""
    current = load(cache)
    now = datetime.now(timezone.utc)
    if current and not force and now - datetime.fromisoformat(current["fetched_at"]) < max_age:
        return f"official CPI airfare: copy from {current['fetched_at']} is recent, kept"
    try:
        with httpx.Client(timeout=30, verify=tls_context(), headers={"user-agent": "GARUDA airfare index (SIH26056)"}) as client:
            series = fetch(client, now.date())
    except Exception as e:  # noqa: BLE001  (offline start must still work)
        log.warning("official CPI airfare: could not refresh (%s); keeping the saved copy", e)
        return f"official CPI airfare: refresh failed ({type(e).__name__}); {'saved copy kept' if current else 'no copy yet'}"
    cache.parent.mkdir(parents=True, exist_ok=True)
    doc = {"item": ITEM, "source": {"name": "MoSPI eSankhyiki, CPI (base 2024)", "url": PORTAL_URL, "api": API_URL}, "fetched_at": now.isoformat(timespec="seconds"), "series": series}
    cache.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return f"official CPI airfare: {len(series)} months, latest {series[-1]['month']} = {series[-1]['index']}"


@dataclass(frozen=True)
class Link:
    month: str  # 'YYYY-MM' used to link
    garuda_days: int
    factor: float  # official(m) / geometric mean of GARUDA's daily values in m
    latest_period: date
    latest_value: float  # GARUDA's latest national index on the 2024 = 100 scale


def link_to_official(national: Sequence[tuple[date, float]], official: Sequence[dict], min_days: int = LINK_MIN_DAYS) -> Link | None:
    """Chain-link GARUDA's daily national index to the official monthly series, or None if no month overlaps enough."""
    if not national:
        return None
    by_month: dict[str, list[float]] = {}
    for period, value in national:
        by_month.setdefault(period.strftime("%Y-%m"), []).append(value)
    for point in reversed(official):
        values = by_month.get(point["month"], [])
        if len(values) >= min_days:
            factor = point["index"] / float(np.exp(np.log(values).mean()))
            latest_period, latest = max(national)
            return Link(point["month"], len(values), factor, latest_period, latest * factor)
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(refresh(force=True))
