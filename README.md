# GARUDA — Real-time Airfare Price Index

A CPI-methodology-aligned price index for Indian domestic airfares: a national sub-index
(base period = 100) that MoSPI could plug into CPI Division 07 (Transport). Built for
Smart India Hackathon problem SIH26056.

It is a measurement system, not a fare-search app: fares are collected on a fixed
specification, turned into route indices with the Jevons formula, and weighted into a
national index by DGCA passenger traffic.

## Run it

Prerequisites: [uv](https://docs.astral.sh/uv/) (it fetches Python 3.11 itself), Node 18+ and
[pnpm](https://pnpm.io/). On Windows, the live scraper uses the installed Microsoft Edge.

```bash
pnpm start
```

That one command installs everything, seeds the database on first run (14 days of
synthetic fares), builds the index, and starts:

- Dashboard: **http://localhost:5173**
- API: http://127.0.0.1:8000 (interactive docs at `/docs`)

Stop with Ctrl+C. It is safe to re-run; an existing database is kept.

| Command | What it does |
|---|---|
| `pnpm start` | Set up (first run) and run the API + dashboard |
| `pnpm reseed` | Wipe and reseed the synthetic data, rebuild the index |
| `pnpm scrape` | Live scrape batch (Akasa Air) → ingest → rebuild index |
| `pnpm scrape --airline QP --route DEL-BOM` | Narrow live scrape, about 30 seconds |
| `pnpm scrape:offline` | Replay 3 cached real fares, no network |
| `pnpm test` | Backend tests + frontend type-check, build and lint |

## Demo click-path (3 minutes)

Before recording, run `pnpm reseed` so the headline number is the clean seeded index
(live rows mixed into the synthetic seed move today's value; see Limitations).

1. **National Index** — "This is the national domestic airfare sub-index. Today it stands
   at *[headline number]*, against a base week of 100." Point at the spike on the trend line.
2. **Route Explorer → DEL-BOM** — "The busiest route in the basket, 18% of the weight. Its
   own Jevons index, the anomaly day marked, and the average fare by carrier."
3. **Yield Curve → DEL-BOM** — "Booking 1 day ahead costs about 2.1× booking 30 days ahead.
   This is the yield-management spread; no Indian data system tracks it today."
4. **Anomaly Alerts** — "This alert fired automatically: the route rose more than two standard
   deviations and more than 5% above its previous week. A real fare shock would trigger it the
   same way." Click the route to jump back to its chart.
5. **CPI Export** — "Route, period, index value, weight, base period: the shape MoSPI's CPI
   series consumes. Pick a date range and download."
6. **Live** — in a terminal, `pnpm scrape --airline QP --route DEL-BOM`. The header strip
   switches to "Akasa Air live" within a minute (or on refresh) and the index updates.
   "These fares were just pulled from Akasa Air's own site."

## Methodology

| Step | Rule |
|---|---|
| Collection | 10 busiest routes × 3 airlines × advance windows 1/7/14/30 days × departures on Tuesday and Saturday; economy, lowest available fare, taxes included (mirrors the US BLS airfare spec) |
| Cleaning | Fares below ₹500 or above ₹50,000 are dropped |
| Missing fares | Carried forward from the last observation and flagged `imputed` |
| Route index | **Jevons**: geometric mean of price relatives against each quote's base-week price. Never the arithmetic mean |
| National index | DGCA-weighted arithmetic mean of route indices (Young / modified Laspeyres) |
| Anomalies | Route index more than 2σ above its previous 7 days **and** at least 5% higher |

Worked check: prices 110, 120, 130 against a base of 100 each give
(1.1 × 1.2 × 1.3)^(1/3) × 100 = **119.72**, not the arithmetic 120 (`backend/tests/test_engine.py`).

## Layout

```
backend/    FastAPI + SQLModel + SQLite, index engine, pipeline, scrapers   (see backend/README.md)
  app/engine/     jevons, aggregate, anomaly, yield_curve (pure functions, unit-tested)
  app/pipeline/   clean, impute, ingest
  app/scraper/    base, akasa (live), indigo / airindia (not scraped: see backend/README.md), scheduler
frontend/   React + Vite + TypeScript + Recharts + Tailwind dashboard
CLAUDE.md   project constitution (methodology rules the code must follow)
QA_REPORT.md  test results and known limitations
```

## Limitations

See [QA_REPORT.md](QA_REPORT.md). In short: only Akasa Air is scraped live (IndiGo's
robots.txt forbids it; Air India sits behind bot protection), the base period is the first
seeded week rather than 2024, and live fares are compared against a synthetic base until a
real base week has been collected.
