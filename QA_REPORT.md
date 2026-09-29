# GARUDA — QA report (M6)

Run on 25 Sep 2026, Windows 11, Python 3.11.16, Node 24, pnpm 12. Command: `pnpm test`.

## Result: all green

| Area | Tests | Result |
|---|---|---|
| Index engine: Jevons, aggregation, anomaly, yield curve, clean, impute, same-day geometric mean (`test_engine.py`) | 16 | PASS |
| Synthetic seed: row count, yield-curve shape, weights, outlier bounds, idempotent reference-data refresh (`test_seed.py`) | 4 | PASS |
| New sources: SpiceJet calendar parsing and coverage, same-airport check, official MoSPI series parsing, chain-linking, `/api/official/cpi-airfare`, offline refresh, `--watch` start-up rule (`test_sources.py`) | 9 | PASS |
| Index build on seeded data: rows written, base ≈ 100, planted spike flagged (`test_build_index.py`) | 3 | PASS |
| API: every endpoint, filters, 404 / 422, CSV format, CORS (`test_api.py`) | 10 | PASS |
| Scraper & batch: collection plan, parsing, ingest, idempotency, failure isolation, dry-run, unavailable airlines, same-airport cross-check, daily catch-up (`test_scraper.py`) | 13 | PASS |
| Edge cases (`test_edge_cases.py`) | 7 | PASS |
| Demo vs live databases: `?dataset=` switch, live bootstrap, live index leaves demo untouched (`test_datasets.py`) | 3 | PASS |
| Smoke: `/health` (`test_smoke.py`) | 1 | PASS |
| **Backend total** | **66** | **PASS** |
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
| Live scrape, SpiceJet, all 10 routes (29 Sep 2026) | 33 real fares from the 6 routes SpiceJet flies; index rebuilt |
| Data accuracy, SpiceJet (`pnpm verify --airline SG`) | 5/5 exact matches; the other 3 dates had no SpiceJet flight in either source |
| Official MoSPI CPI airfare series (`pnpm official`) | 20 months downloaded (Jan 2025 – Aug 2026; Aug 2026 = 135.49); shown on the National Index view |
| Collector (`--watch`, used by `pnpm start`) | Collects on start (unless the last capture is under 30 min old), then every 6 hours |
| Dashboard dataset switch | Demo and Live views render; choice remembered; views refresh when new data lands |
| Offline replay (`--dry-run`) | Works without network; no duplicates on repeat |
| Header strip after live / offline / no scrape | Shows index date, fare counts by source, last scrape time (IST) and per-airline status |

## Known limitations (documented, not bugs)

1. **Live coverage is Akasa Air + SpiceJet (6.7% of domestic passengers, DGCA Aug 2026).**
   IndiGo's and Air India Express's robots.txt disallow automated search, so they are
   deliberately not scraped. Air India's fares sit behind Akamai Bot Manager, which we do not
   try to defeat. Sanctioned alternatives (a
   statutory data request, licensed fare feeds, an agency partnership) are listed in
   `backend/README.md`. IndiGo and Air India fares in the demo are synthetic.
2. **BOM-GOI has no Akasa data.** Akasa appears to serve Goa via Mopa (GOX), not Dabolim
   (GOI). The basket is unchanged; the batch logs the route and moves on.
3. **GARUDA's own base is its first week of data, not 2024.** Every screen and export row states
   the actual base period. The official MoSPI series (base 2024 = 100) is shown alongside, and
   GARUDA is chain-linked onto it automatically once it has 7+ days inside a month MoSPI has
   published (for the live data: September 2026, once MoSPI releases it).
4. **The live index is provisional for its first 7 days** while its base week fills up, and it
   covers Akasa Air only. The dashboard says both in a banner on the Live view.
5. **Collection window is a minimum lead time.** The departure priced for "7 days ahead,
   Tuesday" is the first Tuesday at least 7 days out, so the actual lead time can be up to 6
   days longer.
6. **Base fares in the seed are estimates** (`backend/app/seed.py`). Market shares are cited:
   DGCA domestic traffic, August 2026.
7. **`pnpm start` uses fixed ports 8010 and 5174.** If either is taken (usually by an
   earlier `pnpm dev` or `uvicorn` still running), `scripts/check-ports.mjs` stops the start
   with a plain message saying which port is busy and how to free it.
8. **Test-client deprecation warning.** pytest prints one Starlette warning about `httpx`; it
   does not affect results.
9. **The live collector runs only while `pnpm start` is running** (it collects on every start
   and every 6 hours). Days when the computer is off are missing; the index carries the last fares forward (flagged `imputed`) until the next
   collection. For unattended collection, schedule `pnpm scrape` daily with Windows Task
   Scheduler or run the project on a small always-on server.
