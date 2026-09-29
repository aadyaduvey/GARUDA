"""Scrape batch: scrape -> ingest -> rebuild index, into the LIVE database (never the demo one).
One failing airline never stops the batch.

  uv run python -m app.scraper.scheduler              # one live batch now
  uv run python -m app.scraper.scheduler --dry-run    # offline: cached sample rows, no network
  uv run python -m app.scraper.scheduler --watch      # keep running (what `pnpm start` uses): a batch
                                                      # now, then one every REFRESH_HOURS hours

Several batches on one day are fine: the index combines a quote's same-day prices by geometric
mean (pipeline/impute.py). Each batch also refreshes the official MoSPI CPI airfare series.
"""
import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, func, select

from app import official
from app.bootstrap import bootstrap_live
from app.build_index import build
from app.db import DATA_DIR, SCRAPER_STATUS_FILE, live_engine
from app.models import IST, Fare, Route
from app.pipeline.ingest import ingest
from app.scraper.airindia import AirIndiaScraper
from app.scraper.akasa import AkasaScraper
from app.scraper.base import FareRow, Scraper, ScraperError, today_ist
from app.scraper.indigo import IndigoScraper
from app.scraper.spicejet import SpiceJetScraper

log = logging.getLogger("garuda.scheduler")

SCRAPERS: dict[str, Scraper] = {s.airline: s for s in (AkasaScraper(), SpiceJetScraper(), IndigoScraper(), AirIndiaScraper())}
CACHE_DIR = DATA_DIR / "pre_collected"
STATUS_FILE = SCRAPER_STATUS_FILE
DRY_RUN_ROWS = 3
REFRESH_HOURS = 6  # --watch: collect again this often while running
MIN_GAP = timedelta(minutes=30)  # --watch: skip the start-up batch if fares arrived this recently (quick restarts)


def cache_path(scraper: Scraper, cache_dir: Path) -> Path:
    return cache_dir / f"{scraper.source}.json"


def cached_rows(scraper: Scraper, cache_dir: Path) -> list[FareRow]:
    """Real rows saved from this scraper's last successful live run (original timestamps kept)."""
    path = cache_path(scraper, cache_dir)
    if not path.exists():
        raise ScraperError(f"no cached sample at {path}; run a live batch first")
    return [FareRow.from_json(d) for d in json.loads(path.read_text(encoding="utf-8"))][:DRY_RUN_ROWS]


def save_sample(scraper: Scraper, rows: list[FareRow], cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path(scraper, cache_dir).write_text(json.dumps([r.to_json() for r in rows[:DRY_RUN_ROWS]], indent=2), encoding="utf-8")


def run_batch(
    airlines: list[str] | None = None,
    routes: list[str] | None = None,
    dry_run: bool = False,
    eng: Engine = live_engine,
    scrapers: dict[str, Scraper] = SCRAPERS,
    cache_dir: Path = CACHE_DIR,
    status_file: Path = STATUS_FILE,
) -> dict:
    """Run every scraper (or the chosen ones), ingest their rows, rebuild the index if anything new arrived.

    Status per airline: ok, no_data, failed (logged, batch continues) or unavailable (deliberately not scraped).

    Returns the batch report, also written to `status_file` for the dashboard.
    """
    today = today_ist()
    with Session(eng) as session:
        basket = [(r.origin, r.destination) for r in session.exec(select(Route).order_by(Route.dgca_weight.desc()))]
    if routes:
        basket = [r for r in basket if f"{r[0]}-{r[1]}" in routes]

    sources, inserted = [], 0
    for code in airlines or list(scrapers):
        scraper = scrapers[code]
        status = {"airline": code, "name": scraper.name, "status": "failed", "rows": 0, "inserted": 0, "duplicates": 0, "rejected": {}, "error": None}
        if scraper.unavailable:
            status.update(status="unavailable", error=scraper.unavailable)
            log.info("%s: not scraped (%s)", scraper.name, scraper.unavailable)
            sources.append(status)
            continue
        try:
            rows = cached_rows(scraper, cache_dir) if dry_run else scraper.scrape(basket, today)
            with Session(eng) as session:
                result = ingest(session, rows)
            if rows and not dry_run:
                save_sample(scraper, rows, cache_dir)
            status.update(
                status="ok" if rows else "no_data",
                rows=len(rows),
                inserted=result.inserted,
                duplicates=result.duplicates,
                rejected=dict(result.rejected),
            )
            inserted += result.inserted
            log.info("%s: %d rows, %d new, %d duplicate", scraper.name, len(rows), result.inserted, result.duplicates)
        except Exception as e:  # noqa: BLE001  (a scraper failure must never crash the batch)
            status["error"] = f"{type(e).__name__}: {e}"
            log.error("%s failed: %s", scraper.name, status["error"])
        sources.append(status)

    rebuilt = False
    if inserted:
        try:
            build(eng)
            rebuilt = True
        except Exception as e:  # noqa: BLE001
            log.error("index rebuild failed: %s", e)

    report = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "dry_run" if dry_run else "live",
        "index_rebuilt": rebuilt,
        "sources": sources,
    }
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def last_collected_at(eng: Engine = live_engine) -> datetime | None:
    """When the newest scraped (non-synthetic) fare was captured, or None."""
    with Session(eng) as session:
        last = session.exec(select(func.max(Fare.scrape_ts)).where(Fare.source != "synthetic")).one()
    if last is None:
        return None
    return last if last.tzinfo else last.replace(tzinfo=timezone.utc)  # SQLite returns UTC without tzinfo


def collected_today(eng: Engine = live_engine) -> bool:
    """True if the database already holds a scraped (non-synthetic) fare from today, IST."""
    last = last_collected_at(eng)
    return last is not None and last.astimezone(IST).date() == today_ist()


def start_up_batch_due(last: datetime | None, now: datetime, min_gap: timedelta = MIN_GAP) -> bool:
    """--watch collects on every start, unless the last capture is only minutes old."""
    return last is None or now - last >= min_gap


def print_report(report: dict) -> None:
    print(f"\nBatch {report['mode']} at {report['run_at']}  (index rebuilt: {report['index_rebuilt']})")
    for s in report["sources"]:
        detail = s["error"] or f"{s['rows']} rows, {s['inserted']} new, {s['duplicates']} duplicate"
        if s["rejected"]:
            detail += f", rejected {s['rejected']}"
        print(f"  {s['name']:<10} {s['status']:<8} {detail}")


def main() -> None:
    parser = argparse.ArgumentParser(description="GARUDA airfare scrape batch.")
    parser.add_argument("--dry-run", action="store_true", help="offline: ingest cached sample rows, no network")
    parser.add_argument("--airline", action="append", choices=sorted(SCRAPERS), help="limit to these IATA codes")
    parser.add_argument("--route", action="append", help="limit to these routes, e.g. DEL-BOM")
    parser.add_argument("--watch", "--daily", dest="watch", action="store_true", help=f"stay running: a batch now, then every {REFRESH_HOURS} hours")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    log.info("live database: %s", bootstrap_live())

    def job() -> None:
        if not args.dry_run:
            log.info(official.refresh())
        print_report(run_batch(airlines=args.airline, routes=args.route, dry_run=args.dry_run))

    if not args.watch:
        job()
        return

    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    last = last_collected_at()
    if start_up_batch_due(last, datetime.now(timezone.utc)):
        log.info("collecting fresh fares now")
        job()
    else:
        log.info("fares were collected at %s (under %d min ago): skipping the start-up batch", last.astimezone(IST).strftime("%H:%M IST"), MIN_GAP.seconds // 60)
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(job, IntervalTrigger(hours=REFRESH_HOURS), misfire_grace_time=3600, coalesce=True)
    log.info("next batch in %d hours, then every %d hours; Ctrl+C to stop", REFRESH_HOURS, REFRESH_HOURS)
    scheduler.start()


if __name__ == "__main__":
    main()
