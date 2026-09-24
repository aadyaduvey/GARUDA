# GARUDA — Claude Code Development Orchestration
## Solo build with Claude Code | Target: demoable PoC in 4 days
## SIH26056 — Real-time Airfare Price Index for CPI Augmentation | MoSPI

---

## 0. THE BUILD PHILOSOPHY (read once, then execute)

**Backwards-from-scraper rule:** The scraper is the riskiest, flakiest component. Build it LAST. Seed the DB with realistic synthetic fares on Day 1 so index + API + dashboard are fully demoable before any real scraping exists. A broken scraper must never be able to break the demo.

**One vertical slice at a time:** Each milestone ends with something you can run and see. No milestone is "done" until its acceptance gate passes.

**You are the reviewer, Claude Code is the implementer.** Every milestone has an acceptance gate written for YOU to verify. Do not move to the next milestone until the gate passes. Never let Claude Code self-certify.

**Locked stack (do not let the agent drift):**
- Backend: Python 3.11, FastAPI, SQLModel, SQLite (PoC only; Postgres is a Phase-2 swap)
- Scraper: Playwright (Python) with playwright-stealth
- Stats: pandas, numpy
- Frontend: React + Vite + TypeScript + Recharts + Tailwind
- Package mgmt: uv (Python), pnpm (JS). Fall back to pip/npm if unavailable.

---

## 1. PREREQUISITES (install before you paste anything)

```bash
# Python 3.11+, Node 18+, git required
python3 --version
node --version

# Install uv (fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pnpm
npm install -g pnpm

# Confirm Claude Code is installed and authenticated
claude --version
```

Create the project folder and start Claude Code inside it:
```bash
mkdir garuda && cd garuda
git init
claude
```

---

## 2. FIRST PASTE — SCAFFOLD THE REPO

Paste this as your very first message to Claude Code. It sets up the whole skeleton so every later prompt has a home.

```
Scaffold a monorepo named "garuda" for a real-time airfare price index system.
Create this exact structure with placeholder files and README stubs, do not
implement logic yet:

garuda/
├── CLAUDE.md                (I will paste content next)
├── backend/
│   ├── pyproject.toml       (deps: fastapi, uvicorn, sqlmodel, pandas, numpy, playwright, playwright-stealth, apscheduler, httpx, pytest)
│   ├── app/
│   │   ├── main.py          (FastAPI app entry)
│   │   ├── db.py            (SQLite engine + session)
│   │   ├── models.py        (SQLModel tables)
│   │   ├── schemas.py       (Pydantic response models)
│   │   ├── seed.py          (synthetic data generator)
│   │   ├── api/
│   │   │   ├── routes_index.py
│   │   │   ├── routes_fares.py
│   │   │   └── routes_export.py
│   │   ├── engine/
│   │   │   ├── jevons.py
│   │   │   ├── aggregate.py
│   │   │   ├── anomaly.py
│   │   │   └── yield_curve.py
│   │   ├── pipeline/
│   │   │   ├── ingest.py
│   │   │   ├── clean.py
│   │   │   └── impute.py
│   │   └── scraper/
│   │       ├── base.py
│   │       ├── indigo.py
│   │       ├── airindia.py
│   │       ├── akasa.py
│   │       └── scheduler.py
│   └── data/
│       ├── route_basket.csv
│       └── pre_collected/
├── frontend/
│   └── (Vite React TS app, scaffold with pnpm create vite)
└── .claude/
    └── agents/              (I will add subagent files next)

Use uv for the backend and pnpm for the frontend. After scaffolding, print the
tree and the exact commands to run backend and frontend dev servers. Stop there.
```

**Acceptance gate M0:** The tree exists. `uv run uvicorn app.main:app` starts (even if it returns nothing useful). `pnpm dev` serves a blank Vite page. If both servers start, proceed.

---

## 3. SECOND PASTE — THE PROJECT CONSTITUTION (CLAUDE.md)

Tell Claude Code to write this to `CLAUDE.md`. This keeps the agent from drifting across sessions.

```
Write the following to CLAUDE.md verbatim:

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
```

**Acceptance gate:** CLAUDE.md exists with this content. From now on, start focused sessions with "Read CLAUDE.md first" so the agent stays anchored.

---

## 4. THIRD PASTE — DEFINE THE SUBAGENT ROLES

Your 6 human roles become 6 Claude Code subagents. For a solo sprint you can run milestones sequentially in the main session, OR invoke a subagent for a focused chunk (useful to run frontend and backend work without polluting context). Create them once.

```
Create these subagent definition files under .claude/agents/, each as a markdown
file with YAML frontmatter (name, description, tools) and a system-prompt body.
Keep each body under 200 words and make it read CLAUDE.md first.

1) .claude/agents/data-engineer.md
   description: Owns DB models, synthetic seed, ingestion/clean/impute pipeline.
   tools: Read, Write, Edit, Bash, Grep, Glob
   body: You build the data layer. Models in models.py, seed in seed.py
   producing realistic fares with a proper yield curve (30d cheapest, 1d
   dearest), 10 routes x 3 airlines x 4 windows x 2 DOW x 14 days. Cleaning
   drops outliers, imputation carries forward. Always write a unit test with a
   tiny fixture. Read CLAUDE.md first.

2) .claude/agents/stats-engine.md
   description: Owns Jevons elementary index, national aggregation, anomaly, yield curve.
   tools: Read, Write, Edit, Bash, Grep, Glob
   body: You implement the statistical core. jevons.py = geometric mean of price
   relatives, NEVER arithmetic. aggregate.py = DGCA-weighted mean of route
   indices. anomaly.py = z-score>2 on 7-day rolling. yield_curve.py = fare vs
   advance-days. Every function pure + unit-tested against a hand-computed
   fixture. Read CLAUDE.md first.

3) .claude/agents/api-dev.md
   description: Owns FastAPI endpoints and Pydantic schemas.
   tools: Read, Write, Edit, Bash, Grep, Glob
   body: You expose the engine over HTTP. Endpoints: GET /api/index/national,
   /api/index/route/{id}, /api/fares, /api/anomalies, /api/yield-curve/{id},
   /api/export/cpi (CSV). Typed schemas only. Add /health. Test with httpx.
   Read CLAUDE.md first.

4) .claude/agents/frontend-dev.md
   description: Owns the React dashboard, 5 views, Recharts, projector-friendly.
   tools: Read, Write, Edit, Bash, Grep, Glob
   body: You build the MoSPI dashboard. Views: National Index, Route Explorer,
   Yield Curve, Anomalies, CPI Export. Government/institutional look: dark-blue
   headers, white bg, large fonts, high contrast. Consume the API; mock it if
   the API is not ready. Read CLAUDE.md first.

5) .claude/agents/scraper-dev.md
   description: Owns Playwright scrapers and scheduler. Built LAST.
   tools: Read, Write, Edit, Bash, Grep, Glob
   body: You build resilient scrapers returning (airline, route, amount,
   fare_class, scrape_ts). Playwright + stealth, random 2-5s delays, UA
   rotation. Output must match the fare ingestion schema exactly. Provide a
   --dry-run that returns cached sample data for demos. Read CLAUDE.md first.

6) .claude/agents/qa.md
   description: Owns tests, edge cases, and the acceptance-gate checklist.
   tools: Read, Write, Edit, Bash, Grep, Glob
   body: You verify. Write pytest for engine + pipeline, httpx tests for API.
   Edge cases: zero fares for a route, single-airline route, division by zero
   in Jevons, empty date range on export. Produce a short PASS/FAIL report.
   Never modify logic to force a pass; report the failure. Read CLAUDE.md first.
```

**Acceptance gate:** Six files exist under `.claude/agents/`. Run `/agents` in Claude Code to confirm they are recognized.

---

## 5. THE MILESTONES (copy-paste prompts + gates)

Run these in order. Each is a fresh focused instruction. Invoke the named subagent, or just paste into the main session.

### M1 — Data layer + synthetic seed (Day 1 morning)
```
Use the data-engineer subagent. Read CLAUDE.md.
1. Implement models.py with the canonical tables.
2. Implement db.py (SQLite at backend/data/garuda.db).
3. Load backend/data/route_basket.csv with the top 10 routes and DGCA weights.
   Use these weight proxies (share of the 10-route basket, normalized):
   DEL-BOM 0.18, BOM-DEL 0.17, DEL-BLR 0.12, BLR-DEL 0.11, DEL-HYD 0.09,
   BOM-BLR 0.08, DEL-CCU 0.08, BOM-GOI 0.07, BLR-PNQ 0.05, DEL-MAA 0.05.
4. Implement seed.py: generate 14 days of fares, 10 routes x 3 airlines
   (IndiGo, Air India, Akasa) x 4 advance windows x 2 DOW. Fares must follow a
   realistic yield curve: 30d cheapest, rising through 14d, 7d, steep at 1d.
   Add small daily noise and one deliberate anomaly spike on DEL-BOM day 10.
5. Add a uv command to wipe+reseed. Print row counts.
Write a unit test asserting seed produces the expected row count and that
1-day fares > 30-day fares on average.
```
**Gate M1:** Reseed runs, DB has ~3,360 fare rows, test passes, 1d > 30d holds.

### M2 — Index engine (Day 1 afternoon)
```
Use the stats-engine subagent. Read CLAUDE.md.
Implement jevons.py, aggregate.py, anomaly.py, yield_curve.py against the
seeded DB. jevons.py MUST be geometric mean of price relatives vs the first
seeded week as base. aggregate.py applies DGCA route weights. anomaly.py flags
z>2 on 7-day rolling per route. Write index_value rows back to the DB.
Add unit tests with a 3-number hand-computed Jevons fixture I can verify by hand.
Print the current national index value and any anomaly flags.
```
**Gate M2:** National index prints a sensible number near 100. The DEL-BOM day-10 spike is flagged. Hand-check the Jevons fixture: for prices [110,120,130] vs base [100,100,100], index = (1.1*1.2*1.3)^(1/3) ≈ 1.1972, so 119.72. Verify the code returns the geometric mean, not the arithmetic 120.

### M3 — API layer (Day 2 morning)
```
Use the api-dev subagent. Read CLAUDE.md.
Wire all endpoints to the engine + DB: /api/index/national (with time series),
/api/index/route/{id}, /api/fares (filterable), /api/anomalies,
/api/yield-curve/{id}, /api/export/cpi (CSV: route, period, index_value,
weight, base_period), /health. Typed schemas. Add CORS for localhost:5173.
Write httpx tests hitting each endpoint. Print curl examples for each.
```
**Gate M3:** `curl /api/index/national` returns a JSON time series. `curl /api/export/cpi` downloads a valid CSV. All httpx tests pass.

### M4 — Dashboard (Day 2 afternoon + Day 3)
```
Use the frontend-dev subagent. Read CLAUDE.md.
Build 5 views wired to the API:
1. National Index Overview: headline number + trend line chart.
2. Route Explorer: route dropdown, route index chart, carrier breakdown bar.
3. Yield Curve: 4-line chart (1/7/14/30d) for selected route.
4. Anomaly Alerts: table with route, date, z-score, severity.
5. CPI Export: date range + download button + CSV preview.
Institutional theme (dark-blue header, white bg, large fonts). Test on a
1920x1080 and a 1024x768 viewport. Handle empty/loading/error states.
```
**Gate M4:** All 5 views render real data from the API. The whole thing works end to end on seeded data. THIS IS YOUR DEMOABLE MILESTONE. Record a backup screen capture here.

### M5 — Scraper (Day 3 evening + Day 4)
```
Use the scraper-dev subagent. Read CLAUDE.md.
Build base.py + one working scraper first: pick the easiest target between
Akasa Air direct and Cleartrip. Return rows matching the fare schema exactly.
Add --dry-run returning 3 cached sample rows for demos. Then implement
scheduler.py to run a daily batch. Then attempt IndiGo and Air India; if
anti-bot blocks them, document the mitigation and keep --dry-run as fallback.
Wire live-scraped rows through pipeline/ingest.py into the DB so the index
updates. Do NOT let a scraper failure crash the batch; log and continue.
```
**Gate M5:** At least one airline scrapes a real fare into the DB and the index updates. `--dry-run` works offline. A failed scraper logs and does not crash the run.

### M6 — Polish + demo hardening (Day 4)
```
Use the qa subagent. Read CLAUDE.md.
1. Run all tests, produce a PASS/FAIL report.
2. Add the edge-case tests (zero fares, single airline, empty export range).
3. Add a "data freshness / scraper status" strip to the dashboard header
   (last run time, sources ok/failed).
4. Add a README with one command to start everything and a demo click-path.
5. Confirm the app runs cold on a fresh clone with seed + one command.
```
**Gate M6:** Fresh clone → one command → working demo. QA report is all green or every red is a known, documented limitation.

---

## 6. THE 4-DAY MAP (solo)

| Day | Milestones | End-of-day state |
|---|---|---|
| Day 1 | M0, M1, M2 | Index computes on seeded data |
| Day 2 | M3, start M4 | API live, dashboard skeleton on real data |
| Day 3 | Finish M4, start M5 | Full dashboard demoable; scraper started |
| Day 4 | M5, M6 | PoC complete, demo recorded |

If Day 1 to 4 slips, cut M5 (real scraper) entirely and demo on seeded plus any pre-collected data. The index is the product; the scraper is evidence.

---

## 7. HOW TO DRIVE CLAUDE CODE EACH SESSION

- Start each session: `Read CLAUDE.md, then <the milestone prompt>`.
- After each milestone: run the gate yourself. If it fails, paste the exact
  error back and say "fix, do not change the methodology or fake data."
- Commit after every green gate: `git add -A && git commit -m "M<n>: <gate>"`.
- If context gets messy, start a fresh session and re-anchor with CLAUDE.md.
- Use `/agents` to invoke a subagent for a focused chunk; use the main session
  for cross-cutting integration.
- Never accept "it should work now" without running the gate. You are the judge.

---

## 8. GUARDRAILS — MAKE THE AGENT STOP IF

- It tries to switch Jevons to arithmetic mean or "simplify" the index math. STOP.
- It invents fake fare numbers to make a gate pass. STOP.
- It adds blockchain, an LLM, or "AI fare prediction". Out of scope. STOP.
- It swaps the stack (Django, Mongo, Next.js) without being asked. STOP.
- It builds the scraper before M1 to M4 are green. Wrong order. STOP.

---

## 9. THE WINNING DEMO PATH (3 minutes)

```
1. National Index Overview: "This is the national domestic airfare sub-index,
   Base 2024=100. Today it stands at [X]."
2. Route Explorer → DEL-BOM: "Busiest route by airport pair. Here is its
   index and carrier breakdown. IndiGo at 66% market share drives it."
3. Yield Curve → DEL-BOM: "30-day booking vs 1-day booking. This premium is
   the yield-management spread. No Indian data system tracks this today."
4. Anomaly Alerts: "This flag fired on [date]. During the Dec 2025 IndiGo
   crisis, this alert would have triggered automatically."
5. CPI Export: "This CSV is in MoSPI's format. Route, period, index, weight,
   base period. Plug-and-play into the CPI 2024 series."
6. (If live scraping works) Terminal: show a fare pulled live from an airline
   site appearing in the dashboard within 30 seconds. "This is live, not cached."
```

---

*Hand this file to Claude Code. Start with Section 2 (First Paste). Verify every
gate yourself before advancing. Build to M4 before worrying about the scraper.*
