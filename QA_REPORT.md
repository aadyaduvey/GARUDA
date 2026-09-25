# GARUDA — QA report (M6)

Run on 25 Sep 2026, Windows 11, Python 3.11.16, Node 24, pnpm 12. Command: `pnpm test`.

## Result: all green

| Area | Tests | Result |
|---|---|---|
| Index engine: Jevons, aggregation, anomaly, yield curve, clean, impute (`test_engine.py`) | 15 | PASS |
| Synthetic seed: row count, yield-curve shape, weights, outlier bounds (`test_seed.py`) | 3 | PASS |
| Index build on seeded data: rows written, base ≈ 100, planted spike flagged (`test_build_index.py`) | 3 | PASS |
| API: every endpoint, filters, 404 / 422, CSV format, CORS (`test_api.py`) | 10 | PASS |
| Scraper & batch: collection plan, parsing, ingest, idempotency, failure isolation, dry-run, unavailable airlines, same-airport cross-check, daily catch-up (`test_scraper.py`) | 13 | PASS |
| Edge cases (`test_edge_cases.py`) | 7 | PASS |
| Demo vs live databases: `?dataset=` switch, live bootstrap, live index leaves demo untouched (`test_datasets.py`) | 3 | PASS |
| Smoke: `/health` (`test_smoke.py`) | 1 | PASS |
| **Backend total** | **55** | **PASS** |
| Frontend type-check + production build | — | PASS |
| Frontend lint (oxlint) | — | PASS, 0 warnings |

No test makes a network call.

### Edge cases covered

| Case | Expected | Result |
|---|---|---|
| A route with zero fares | Route dropped from the index; national index renormalises over the rest; route endpoints return empty data, not errors | PASS |
| A single-airline route | Route index computed from that airline alone; base week ≈ 100 | PASS |
| A day with no fares for a route | Fares carried forward and flagged `imputed`; index unchanged that day | PASS |
| Zero / out-of-range fares (₹0, ₹120, ₹99,999) | Dropped before Jevons; index identical to without them | PASS |
| Division by zero in Jevons | `jevons()` rejects zero or negative prices and empty input with a clear error | PASS |
| Empty date range on export | CSV with header row only | PASS |
| Reversed date range on export | HTTP 422 | PASS |
| Empty database | Endpoints return empty structures; index build explains how to seed | PASS |
| Scraper failure | Logged, batch continues, other airlines still ingested | PASS |
| Re-running the same capture | No duplicate fares | PASS |

## Manual checks

| Check | Result |
|---|---|
| Fresh clone → `pnpm start` path (install, bootstrap an empty DB, start both servers) | PASS: ready 33 s after a cold start; seeded 3,360 fares; API and dashboard served |
| Dashboard at 1920×1080 and 1024×768, all 5 views | PASS, no console errors |
| Dashboard with the API down | Clear error message with the start command and a retry button |
| Live scrape, Akasa Air, all 10 routes | 72 real fares from 9 routes; index rebuilt |
| Data accuracy (`pnpm verify`): scraped price vs cheapest flight in Akasa's own search, same airports | 8/8 exact matches (DEL-BOM, BLR-DEL; 1/7/14/30-day windows) |
| Other platforms for cross-validation | None usable: MakeMyTrip, Goibibo, ixigo, EaseMyTrip, Yatra, Cleartrip, Kayak, Skyscanner and Google Flights all disallow automated flight search |
| Daily collector (`--daily`) | Starts, catches up if today is missing, schedules 06:00 IST |
| Dashboard dataset switch | Demo and Live views render; choice remembered; views refresh when new data lands |
| Offline replay (`--dry-run`) | Works without network; no duplicates on repeat |
| Header strip after live / offline / no scrape | Shows index date, fare counts by source, last scrape time (IST) and per-airline status |

## Known limitations (documented, not bugs)

1. **Live coverage is Akasa Air only (~5% market share).** IndiGo's robots.txt disallows
   automated search/booking access, so it is deliberately not scraped. Air India's fares sit
   behind Akamai Bot Manager, which we do not try to defeat. Sanctioned alternatives (a
   statutory data request, licensed fare feeds, an agency partnership) are listed in
   `backend/README.md`. IndiGo and Air India fares in the demo are synthetic.
2. **BOM-GOI has no Akasa data.** Akasa appears to serve Goa via Mopa (GOX), not Dabolim
   (GOI). The basket is unchanged; the batch logs the route and moves on.
3. **Base period is the first seeded week, not 2024.** Every screen and export row states the
   actual base period. A 2024 base needs 2024 fare data.
4. **The live index is provisional for its first 7 days** while its base week fills up, and it
   covers Akasa Air only. The dashboard says both in a banner on the Live view.
5. **Collection window is a minimum lead time.** The departure priced for "7 days ahead,
   Tuesday" is the first Tuesday at least 7 days out, so the actual lead time can be up to 6
   days longer.
6. **Market shares and base fares in the seed are estimates** (`backend/app/seed.py`).
   Replace them with cited DGCA figures before quoting them.
7. **`pnpm start` uses fixed ports 8000 and 5173.** If either is taken (usually by an
   earlier `pnpm dev` or `uvicorn` still running), `scripts/check-ports.mjs` stops the start
   with a plain message saying which port is busy and how to free it.
8. **Test-client deprecation warning.** pytest prints one Starlette warning about `httpx`; it
   does not affect results.
9. **The live collector runs only while `pnpm start` is running.** Days when the computer is off
   are missing; the index carries the last fares forward (flagged `imputed`) until the next
   collection. For unattended collection, schedule `pnpm scrape` daily with Windows Task
   Scheduler or run the project on a small always-on server.
