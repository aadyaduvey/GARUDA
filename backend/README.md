# GARUDA backend

FastAPI + SQLModel + SQLite. Index engine (Jevons / DGCA-weighted aggregation),
ingestion pipeline, and Playwright scrapers.

```bash
uv sync
uv run python -m app.seed                  # wipe, seed 14 days of synthetic fares, build the index
uv run uvicorn app.main:app --reload       # API on http://127.0.0.1:8000 (docs at /docs)
uv run pytest
```

## Two databases

`data/garuda.db` holds the **demo** data (synthetic seed only). `data/garuda_live.db` holds
**live** data (real scraped fares only). Every API endpoint takes `?dataset=demo|live`
(default `demo`). Scrapers write to the live database only, so the demo numbers never drift.

## Scrapers

```bash
uv run python -m app.scraper.scheduler                 # one live batch now: scrape -> ingest -> rebuild index
uv run python -m app.scraper.scheduler --dry-run       # offline: ingest 3 cached real rows, no network
uv run python -m app.scraper.scheduler --airline QP --route DEL-BOM   # narrow a run
uv run python -m app.scraper.scheduler --daily         # stay running; batch every day at 06:00 IST
                                                       # (runs one right away if today is missing)
uv run python -m app.scraper.verify                    # cross-check prices against Akasa's own search
```

`pnpm start` (project root) runs the `--daily` collector alongside the API and dashboard.
Opening Akasa's site is retried up to 3 times, since it occasionally resets the first connection.

Each batch writes `data/scraper_status.json` (last run, per-airline ok/failed). A failing
airline is logged and skipped; it never stops the batch or the demo.

The scrapers drive installed Microsoft Edge (`GARUDA_BROWSER_CHANNEL=msedge`, the default).
On a machine without Edge, set `GARUDA_BROWSER_CHANNEL=""` and run `uv run playwright install chromium`.

### What each airline does

| Airline | Status | How |
|---|---|---|
| Akasa Air (QP) | **Live** | Opens akasaair.com in a headless browser (anonymous guest session), then calls the site's own low-fare calendar: one request per route returns the lowest fare, taxes and fees included, for every departure date. 10 routes = 10 requests, 2-5 s apart. |
| IndiGo (6E) | Not scraped | `goindigo.in/robots.txt` disallows automated access to `/search.html`, `/book/*` and `/booking/*` for all user agents. We respect it. |
| Air India (AI) | Not implemented | robots.txt allows search, but fares sit behind Akamai Bot Manager and a multi-step booking API. We do not try to defeat dedicated anti-bot systems. |

Collection rule (mirrors US BLS): for each advance window (1, 7, 14, 30 days) and each
departure day (Tuesday, Saturday), price the first such weekday at least `window` days
ahead. The window is the minimum lead time; the actual one can be up to 6 days longer.

Accuracy check (`app/scraper/verify.py`): for each route it re-prices the Tuesday departures
through Akasa's regular flight search and compares the cheapest flight between the **same two
airports** with the calendar price the scraper stores. On 25 Sep 2026: 8/8 exact matches
(DEL-BOM, BLR-DEL). Akasa's search is city-wide, so it also lists the new Noida (DXN) and
Navi Mumbai (NMI) airports; those are different routes and are excluded.

Known gap: Akasa returns an error for **BOM-GOI**. Akasa appears to serve Goa via Mopa
(GOX), not Dabolim (GOI). The route basket is unchanged; the batch logs it and continues.

### Airlines without a scraper

A national statistics office should not depend on scraping for the two largest carriers.
Sanctioned routes to the same data, in rough order of preference:

1. **Statutory data request.** MoSPI can request fare data from airlines or DGCA under the
   Collection of Statistics Act, 2008, the way BLS and ONS source transport prices.
2. **Licensed fare feeds.** GDS / fare-filing data (e.g. ATPCO, Amadeus, Sabre) cover all
   Indian carriers with published fares.
3. **Partnership with an online travel agency** for an agreed daily extract.

Until then, `--dry-run` keeps the demo working offline, and IndiGo / Air India fares in
the demo database are synthetic (`source = "synthetic"`).

Other platforms were checked on 25 Sep 2026 and **all** disallow automated flight search in
robots.txt: MakeMyTrip, Goibibo, ixigo, EaseMyTrip, Yatra, Cleartrip, Kayak, Skyscanner and
Google Flights.
