"""SpiceJet scraper.

spicejet.com/robots.txt only disallows /api/v1, /public/, /externalBooking and /cgi-bin/
(checked 29 Sep 2026). GARUDA opens the public flight-search page, which fetches the site's
anonymous guest token and its own low-fare calendar; the calendar endpoint (/api/v2/search/lowfare)
is then asked for the other dates. GARUDA never calls /api/v1 itself.

One calendar request returns the lowest fare for 7 departure dates (centre date +/- 3 days);
its total is fareAmount + taxesAndFeesAmount, which equals the cheapest flight's full price in the
site's regular search (/api/v3/search/availability, used by app/scraper/verify.py).
"""
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

from app.scraper.base import ADVANCE_DAYS, FareRow, Scraper, ScraperError, browser_page, polite_delay, select_quotes

log = logging.getLogger("garuda.scraper.spicejet")

SEARCH_PAGE = (
    "https://www.spicejet.com/search?from={origin}&to={destination}&tripType=1&departure={departure}"
    "&adult=1&child=0&srCitizen=0&infant=0&currency=INR&redirectTo=/"
)
LOW_FARE_PATH = "/api/v2/search/lowfare"
SEARCH_PATH = "/api/v3/search/availability"
CALENDAR_HALF_WIDTH = 3  # the calendar covers centerDate - 3 .. centerDate + 3
PAX = {"journeyClass": "ff", "adult": 1, "child": 0, "infant": 0, "srCitizen": 0}

_FETCH_JS = """async ([path, token, body]) => {
  const r = await fetch(path, {method: 'POST', headers: {'content-type': 'application/json',
    accept: 'application/json', authorization: token, os: 'desktop'}, body: JSON.stringify(body)});
  return {status: r.status, text: await r.text()};
}"""


def parse_low_fares(payload: dict) -> dict[date, float]:
    """Departure date -> lowest total fare (taxes included), skipping dates with no flights."""
    fares = {}
    for day in (payload.get("data") or {}).get("lowFareDateMarkets") or []:
        low = day.get("lowestFareAmount")
        if not low or not low.get("fareAmount"):
            continue
        fares[datetime.fromisoformat(day["departureDate"]).date()] = float(low["fareAmount"] + (low.get("taxesAndFeesAmount") or 0))
    return fares


def cheapest_same_airports(payload: dict, origin: str, destination: str) -> float | None:
    """Lowest adult total fare among the searched date's flights between exactly these airports."""
    data = payload.get("data") or {}
    totals: dict[str, float] = {}
    for key, fare in (data.get("faresAvailable") or {}).items():
        adult = [p["fareAmount"] for p in fare.get("passengerFares") or [] if p.get("passengerType") == "ADT"]
        if adult:
            totals[key] = min(adult)
    prices = [
        totals[key]
        for trip in data.get("trips") or []
        for journey in trip.get("journeysAvailable") or []
        if (journey["designator"]["origin"], journey["designator"]["destination"]) == (origin, destination)
        for key in journey.get("fares") or {}
        if key in totals
    ]
    return float(min(prices)) if prices else None


def calendar_centres(today: date) -> list[date]:
    """One calendar request per advance window, centred so it covers that window's Tuesday and Saturday."""
    return [today + timedelta(days=window + CALENDAR_HALF_WIDTH) for window in ADVANCE_DAYS]


OPEN_ATTEMPTS = 3
RETRY_WAIT_S = (15, 45)


@contextmanager
def spicejet_session(origin: str = "DEL", destination: str = "BOM") -> Iterator[tuple["Page", str]]:  # noqa: F821
    """A browser page on SpiceJet's search page plus the guest token the site issued it."""
    url = SEARCH_PAGE.format(origin=origin, destination=destination, departure=(date.today() + timedelta(days=7)).isoformat())
    with browser_page() as page:
        for attempt in range(1, OPEN_ATTEMPTS + 1):
            try:
                with page.expect_request(lambda r: LOW_FARE_PATH in r.url, timeout=60_000) as req:
                    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                token = req.value.headers.get("authorization")
                if not token:
                    raise ScraperError("the search page sent no guest token")
                break
            except Exception as e:
                if attempt == OPEN_ATTEMPTS:
                    raise ScraperError(f"could not open spicejet.com or get a guest token after {attempt} attempts: {e}") from e
                log.warning("SpiceJet: opening the site failed (attempt %d of %d), retrying: %s", attempt, OPEN_ATTEMPTS, str(e).splitlines()[0])
                polite_delay(*RETRY_WAIT_S)
        yield page, token


def _post(page, token: str, path: str, body: dict) -> dict:
    result = page.evaluate(_FETCH_JS, [path, token, body])
    if result["status"] != 200:
        raise ScraperError(f"{path} returned HTTP {result['status']}")
    try:
        return json.loads(result["text"])
    except ValueError as e:
        raise ScraperError(f"unexpected response from {path}: {e}") from e


def fetch_low_fares(page, token: str, origin: str, destination: str, centre: date) -> dict[date, float]:
    body = {"pax": PAX, "codes": {"currency": "INR"}, "origin": origin, "destination": destination, "centerDate": centre.isoformat()}
    return parse_low_fares(_post(page, token, LOW_FARE_PATH, body))


def fetch_flight_search(page, token: str, origin: str, destination: str, departure: date) -> dict:
    """Every flight on `departure`, as the site's own search returns it."""
    body = {"destinationStationCode": destination, "originStationCode": origin, "onWardDate": departure.isoformat(), "currency": "INR", "pax": PAX}
    return _post(page, token, SEARCH_PATH, body)


class SpiceJetScraper(Scraper):
    airline = "SG"
    name = "SpiceJet"
    source = "spicejet_lowfare"

    def scrape(self, routes: list[tuple[str, str]], today: date) -> list[FareRow]:
        rows: list[FareRow] = []
        with spicejet_session() as (page, token):
            for origin, destination in routes:
                calendar: dict[date, float] = {}
                try:
                    for centre in calendar_centres(today):
                        polite_delay()
                        calendar |= fetch_low_fares(page, token, origin, destination, centre)
                except ScraperError as e:
                    log.warning("SpiceJet %s-%s: %s", origin, destination, e)
                    continue
                if not calendar:
                    log.info("SpiceJet %s-%s: no flights in the calendar (route not operated)", origin, destination)
                    continue
                quotes = select_quotes(
                    calendar,
                    today=today,
                    airline=self.airline,
                    origin=origin,
                    destination=destination,
                    scrape_ts=datetime.now(timezone.utc),
                    source=self.source,
                )
                log.info("SpiceJet %s-%s: %d quotes", origin, destination, len(quotes))
                rows += quotes
        return rows
