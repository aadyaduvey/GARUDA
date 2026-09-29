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

That one command installs everything, seeds the demo database on first run (14 days of
synthetic fares), builds the index, and starts three things:

- Dashboard: **http://localhost:5174**
- API: http://127.0.0.1:8010 (interactive docs at `/docs`)
- The **live collector**: scrapes real Akasa Air fares every day at 06:00 IST (and right away if
  today has not been collected yet), then rebuilds the live index. The dashboard picks up new
  data by itself within 30 seconds.

Stop with Ctrl+C. It is safe to re-run; existing databases are kept.

### Open it on another device (phone, second laptop, projector PC)

`pnpm start` is private to this computer. To open the dashboard from another device on the
same Wi-Fi, start it with:

```bash
pnpm start:lan
```

The `web` line prints a **Network** address such as `http://192.168.1.3:5174/`; open that on the
other device. Only the dashboard is exposed; it fetches data through itself, and the API stays
private to this computer.

If the other device cannot connect:

- **Windows Firewall.** On the first run Windows asks whether to allow Node.js; click *Allow*.
  If the Wi-Fi is set to *Public*, Windows blocks it anyway: on a trusted network set it to
  *Private* (Settings → Network & internet → Wi-Fi → your network → Network profile type).
- **Venue or college Wi-Fi** often blocks devices from reaching each other. Turn on your phone's
  hotspot and connect both devices to it instead.
- Both devices must be on the **same** network. Opening it from anywhere on the internet needs a
  deployment or a tunnel, which this PoC does not set up.

### Two datasets

The switch at the top right of the dashboard chooses between:

| Dataset | What it is | Use it for |
|---|---|---|
| **Demo data** | 14 days of synthetic fares for all 3 airlines, with one planted anomaly | The demo: stable numbers that show every feature |
| **Live · Akasa** | Real Akasa Air fares only (~5% of the market), collected daily | Proof it works on real data. Its first 7 days form the base week; until then values are provisional |

Live scrapes never touch the demo data.

| Command | What it does |
|---|---|
| `pnpm start` | Set up (first run) and run the API + dashboard |
| `pnpm start:lan` | Same, but the dashboard can also be opened from other devices on your Wi-Fi |
| `pnpm reseed` | Wipe and reseed the demo data, rebuild its index |
| `pnpm scrape` | One live batch now (Akasa Air) → live database → rebuild live index |
| `pnpm scrape --airline QP --route DEL-BOM` | Narrow live scrape, about 30 seconds |
| `pnpm scrape:offline` | Replay 3 cached real fares into the live database, no network |
| `pnpm verify` | Cross-check scraped prices against Akasa's own flight search (8 checks, ~1 minute) |
| `pnpm test` | Backend tests + frontend type-check, build and lint |

## Demo click-path (3 minutes)

Start on **Demo data** (switch at the top right).

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
6. **Live** — flip the switch to **Live · Akasa**. "This is the same system on real fares,
   collected automatically from Akasa Air every morning since *[first day]*." Optionally run
   `pnpm scrape --airline QP --route DEL-BOM` in a terminal and watch the header update.
7. **Data check** (if asked) — `pnpm verify`: "Every scraped price matches the cheapest flight
   in Akasa's own search for the same airports."

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
robots.txt forbids it; Air India sits behind bot protection, and every other Indian travel
site also forbids automated flight searches), the base period is the first week of data
rather than 2024, and the live collector only runs while `pnpm start` is running.
