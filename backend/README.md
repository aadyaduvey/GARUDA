# GARUDA backend

FastAPI + SQLModel + SQLite. Index engine (Jevons / DGCA-weighted aggregation),
ingestion pipeline, and Playwright scrapers.

```bash
uv sync
uv run python -m app.seed                  # wipe, seed 14 days of synthetic fares (IndiGo, Air India, Akasa), build the index
uv run uvicorn app.main:app --reload --port 8010   # API on http://127.0.0.1:8010 (docs at /docs)
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
uv run python -m app.scraper.scheduler --airline SG --route DEL-BOM   # narrow a run
uv run python -m app.scraper.scheduler --watch         # stay running: a batch now, then every 6 hours
uv run python -m app.scraper.verify                    # cross-check prices against each airline's own search
uv run python -m app.official                          # refresh the official MoSPI CPI airfare series
```

`pnpm start` (project root) runs the `--watch` collector alongside the API and dashboard, so
every start collects fresh fares (unless the last capture is under 30 minutes old) and it keeps
collecting every 6 hours while it runs. When a quote is priced more than once in a day, the index
uses the geometric mean of that day's prices (consistent with Jevons). Opening each airline's
site is retried up to 3 times, since the sites occasionally reset the first connection.

Each batch writes `data/scraper_status.json` (last run, per-airline ok/failed). A failing
airline is logged and skipped; it never stops the batch or the demo.

The scrapers drive installed Microsoft Edge (`GARUDA_BROWSER_CHANNEL=msedge`, the default).
On a machine without Edge, set `GARUDA_BROWSER_CHANNEL=""` and run `uv run playwright install chromium`.

### What each airline does

| Airline | Status | How |
|---|---|---|
| Akasa Air (QP) | **Live** | Opens akasaair.com in a headless browser (anonymous guest session), then calls the site's own low-fare calendar: one request per route returns the lowest fare, taxes and fees included, for every departure date. 10 routes = 10 requests, 2-5 s apart. |
| SpiceJet (SG) | **Live** | Opens SpiceJet's public flight-search page (anonymous guest session), then asks the site's own low-fare calendar (`/api/v2/search/lowfare`, 7 dates per request, total = fare + taxes and fees) for each advance window: 4 requests per route, 2-5 s apart. robots.txt only disallows `/api/v1`, `/public/`, `/externalBooking` and `/cgi-bin/`; GARUDA never calls `/api/v1` itself. SpiceJet flies 6 of the 10 basket routes (not DEL-HYD, BOM-GOI, BLR-PNQ, DEL-MAA). |
| IndiGo (6E) | Not scraped | `goindigo.in/robots.txt` disallows automated access to `/search.html`, `/book/*` and `/booking/*` for all user agents. We respect it. |
| Air India (AI) | Not implemented | robots.txt allows search, but fares sit behind Akamai Bot Manager and a multi-step booking API. We do not try to defeat dedicated anti-bot systems. |
| Air India Express (IX) | Not scraped | `airindiaexpress.com/robots.txt` disallows `/flight-availability`, its search-results page. |

Market shares (`app/seed.py`) are DGCA's domestic figures for August 2026, published 23 Sep
2026: IndiGo 65.0%, Air India Group 26.7%, Akasa Air 5.5%, SpiceJet 1.2%. The live data
therefore covers 6.7% of domestic passengers directly.

Collection rule (mirrors US BLS): for each advance window (1, 7, 14, 30 days) and each
departure day (Tuesday, Saturday), price the first such weekday at least `window` days
ahead. The window is the minimum lead time; the actual one can be up to 6 days longer.

Accuracy check (`app/scraper/verify.py`): for each airline and route it re-prices the Tuesday
departures through the airline's regular flight search and compares the cheapest flight between
the **same two airports** with the calendar price the scraper stores. Akasa, 25 Sep 2026: 8/8
exact matches (DEL-BOM, BLR-DEL). SpiceJet, 29 Sep 2026: 5/5 exact matches (the other 3 dates
had no SpiceJet flight in either source). Akasa's search is city-wide, so it also lists the new
Noida (DXN) and Navi Mumbai (NMI) airports; those are different routes and are excluded.

## Official benchmark (MoSPI eSankhyiki)

`app/official.py` downloads MoSPI's official CPI **Airfare** item index (All India, rural +
urban, item 07.3.3.1.2.01, base 2024 = 100, monthly from January 2025) from MoSPI's open API
`api.mospi.gov.in`, the backend of esankhyiki.mospi.gov.in (robots.txt: `Allow: /`). A copy is
kept in `data/official/cpi_airfare.json` (committed, so the dashboard shows it offline) and
refreshed by `pnpm start` and by every collector batch. `GET /api/official/cpi-airfare` serves
it.

Once GARUDA has at least 7 days inside a month MoSPI has published, the API chain-links GARUDA's
national index to the official series through that month, putting GARUDA on the 2024 = 100 scale:
GARUDA(t) × official(month) / geometric mean of GARUDA's days in that month.

MoSPI's server needs TLS legacy renegotiation, which OpenSSL 3 refuses by default; GARUDA
enables only that option (certificates are still verified), as MoSPI's own Python client does.

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

Other platforms were checked on 25 and 29 Sep 2026 and **all** disallow automated flight search
in robots.txt: MakeMyTrip, Goibibo, ixigo, EaseMyTrip, Yatra, Cleartrip, Paytm, HappyFares,
Kayak, Momondo, Skyscanner, Wego, Trip.com, Expedia, Kiwi.com, Aviasales and Google Flights.
Regional airlines (Alliance Air, Star Air, Fly91) were not added: the basket is the 10 busiest
trunk routes, which they serve little if at all (not yet checked route by route). Amadeus closed
its free self-service fare API on 17 Jul 2026.
