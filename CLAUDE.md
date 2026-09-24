# GARUDA — Project Constitution

## What this is
A CPI-methodology-aligned real-time airfare price index for India. NOT a fare
tracker, NOT a consumer flight-search app. The output is a national domestic
airfare sub-index (Base 2024=100) that MoSPI could plug into CPI Division 07.

## Non-negotiable methodology
- Elementary index = Jevons (geometric mean of price relatives). NEVER use
  arithmetic mean. This is the single most important correctness rule.
- National index = weighted arithmetic mean of route indices, weights from DGCA
  passenger traffic (Young / modified Laspeyres).
- Missing fares = carry-forward imputation, flagged as imputed.
- Outlier filter: drop fares < INR 500 or > INR 50,000 before indexing.

## Stack (do not change without being told)
Backend: Python 3.11, FastAPI, SQLModel, SQLite. Scraper: Playwright.
Stats: pandas, numpy. Frontend: React + Vite + TS + Recharts + Tailwind.

## Build order (backwards from scraper)
1 data models  2 synthetic seed  3 index engine  4 API  5 dashboard  6 scraper.
The system must be fully demoable on seeded data before the scraper is built.

## Data model (canonical)
route(id, origin, destination, dgca_weight)
airline(id, name, code, market_share)
fare(id, route_id, airline_id, amount, advance_days, dep_dow, scrape_ts, source, imputed)
index_value(id, route_id, period, jevons_index, national_index, anomaly_flag)

## Collection specification (mirror US BLS)
Advance windows: 1, 7, 14, 30 days. Days of week: Tuesday, Saturday.
Airlines for PoC: IndiGo, Air India, Akasa. Class: economy, lowest available.

## Conventions
- Every engine function is pure and unit-tested with a tiny fixture.
- API returns typed Pydantic schemas, never raw ORM objects.
- No secrets in code. No network calls in tests.
- Keep functions small. Commit after each passing acceptance gate.

## What "done" means
A milestone is done only when its acceptance gate (defined by the human) passes
when run locally. Never self-certify. Never fake data to pass a gate.

## Out of scope (do not add)
No LLM, no "AI fare prediction", no blockchain. This is a measurement system,
not a prediction toy. Adding these dilutes the CPI-alignment value.
