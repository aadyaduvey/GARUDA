"""Scraper contract, BLS-style collection plan, and a shared polite headless browser.

Every scraper returns FareRow objects, which pipeline/ingest.py maps 1:1 onto the fare table.
"""
import logging
import os
import random
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from app.models import IST

log = logging.getLogger("garuda.scraper")

# Collection specification (CLAUDE.md): advance windows x departure days of week.
ADVANCE_DAYS = (1, 7, 14, 30)
DEP_DOWS = {"TUE": 1, "SAT": 5}  # name -> date.weekday()


class ScraperError(Exception):
    """A scraper could not collect fares (blocked, site changed, network down)."""


@dataclass(frozen=True)
class FareRow:
    airline: str  # IATA code, e.g. "QP"
    origin: str
    destination: str
    amount: float  # INR, lowest available economy fare, taxes and fees included
    advance_days: int  # collection window: 1, 7, 14 or 30
    dep_dow: str  # "TUE" or "SAT"
    dep_date: date  # the departure date that was priced
    fare_class: str  # "economy"
    scrape_ts: datetime  # timezone-aware
    source: str  # e.g. "akasa_lowfare"

    def to_json(self) -> dict:
        d = asdict(self)
        d["dep_date"] = self.dep_date.isoformat()
        d["scrape_ts"] = self.scrape_ts.isoformat()
        return d

    @classmethod
    def from_json(cls, d: Mapping) -> "FareRow":
        return cls(**{**d, "dep_date": date.fromisoformat(d["dep_date"]), "scrape_ts": datetime.fromisoformat(d["scrape_ts"])})


def collection_plan(today: date) -> list[tuple[int, str, date]]:
    """(advance_days, dep_dow, departure date) quotes to price on `today`.

    For each window, the first Tuesday / Saturday at least `window` days ahead, so the
    nominal window is the minimum lead time (the actual one is up to 6 days longer).
    """
    plan = []
    for window in ADVANCE_DAYS:
        earliest = today + timedelta(days=window)
        for dow, weekday in DEP_DOWS.items():
            plan.append((window, dow, earliest + timedelta(days=(weekday - earliest.weekday()) % 7)))
    return plan


def select_quotes(
    low_fares: Mapping[date, float],
    *,
    today: date,
    airline: str,
    origin: str,
    destination: str,
    scrape_ts: datetime,
    source: str,
) -> list[FareRow]:
    """Pick the collection plan's departure dates out of a date -> lowest-fare calendar."""
    return [
        FareRow(airline, origin, destination, low_fares[dep], window, dow, dep, "economy", scrape_ts, source)
        for window, dow, dep in collection_plan(today)
        if dep in low_fares
    ]


def today_ist() -> date:
    return datetime.now(IST).date()


def polite_delay(low: float = 2.0, high: float = 5.0) -> None:
    """Random pause between requests to the same site."""
    time.sleep(random.uniform(low, high))


# Current desktop Chromium user agents on Windows; one is picked per browser session.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
]

# Installed browser to drive. "msedge" works on any Windows machine without a download;
# set GARUDA_BROWSER_CHANNEL="" to use Playwright's bundled Chromium (`uv run playwright install chromium`).
BROWSER_CHANNEL = os.environ.get("GARUDA_BROWSER_CHANNEL", "msedge")


@contextmanager
def browser_page(headless: bool = True) -> Iterator["Page"]:  # noqa: F821
    """A stealth-patched headless page with an Indian locale and a rotated user agent."""
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(channel=BROWSER_CHANNEL or None, headless=headless)
        try:
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                viewport={"width": 1366, "height": 900},
            )
            yield context.new_page()
        finally:
            browser.close()


class Scraper:
    """One airline. `scrape` hits the network; failures raise ScraperError."""

    airline: str  # IATA code
    name: str
    source: str

    def scrape(self, routes: list[tuple[str, str]], today: date) -> list[FareRow]:
        raise NotImplementedError
