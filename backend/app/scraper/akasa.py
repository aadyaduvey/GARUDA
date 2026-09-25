"""Akasa Air scraper.

Loads akasaair.com in a headless browser, which issues the site's anonymous guest token,
then asks the site's own low-fare calendar endpoint for each route: one request returns
the lowest fare (taxes and fees included) for every departure date in the window.

The site's regular flight search (every flight on one date, full price) is used by
app/scraper/verify.py to cross-check the calendar.
"""
import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

from app.scraper.base import ADVANCE_DAYS, FareRow, Scraper, ScraperError, browser_page, polite_delay, select_quotes

log = logging.getLogger("garuda.scraper.akasa")

HOME_URL = "https://www.akasaair.com/"
API = "https://prod-bl.qp.akasaair.com/api/ibe/availability"
LOW_FARE_URL = f"{API}/search/lowFare"
SEARCH_URL = f"{API}/search"
CALENDAR_DAYS = max(ADVANCE_DAYS) + 7  # far enough to cover the longest window's departure day

_FETCH_JS = """async ([url, token, body]) => {
  const r = await fetch(url, {method: 'POST', headers: {'content-type': 'application/json',
    accept: 'application/json', authorization: token}, body: JSON.stringify(body)});
  return {status: r.status, text: await r.text()};
}"""


def parse_low_fares(payload: dict) -> dict[date, float]:
    """Departure date -> lowest fare, skipping dates with no flights or sold out."""
    fares = {}
    for day in (payload.get("data") or {}).get("lowFares") or []:
        if day.get("noFlights") or day.get("soldOut") or not day.get("price"):
            continue
        fares[datetime.fromisoformat(day["date"]).date()] = float(day["price"])
    return fares


def cheapest_same_airports(payload: dict, origin: str, destination: str) -> float | None:
    """Lowest total fare (taxes included) among flights between exactly these two airports.

    The site's search is city-wide, so it also returns other airports in the same city
    (e.g. DXN Noida for Delhi, NMI Navi Mumbai for Mumbai); those are skipped.
    """
    data = payload.get("data") or {}
    totals = {f["key"]: f["value"]["totals"]["fareTotal"] for f in data.get("faresAvailable") or []}
    prices: list[float] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            designator = node.get("designator")
            if isinstance(designator, dict) and "fares" in node:
                if (designator.get("origin"), designator.get("destination")) == (origin, destination):
                    prices.extend(totals[f["fareAvailabilityKey"]] for f in node["fares"] if f.get("fareAvailabilityKey") in totals)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(data.get("results"))
    return float(min(prices)) if prices else None


OPEN_ATTEMPTS = 3
RETRY_WAIT_S = (15, 45)  # the site occasionally resets the first connection; wait and try again


@contextmanager
def akasa_session() -> Iterator[tuple["Page", str]]:  # noqa: F821
    """A browser page on akasaair.com plus the guest token the site issued it."""
    with browser_page() as page:
        for attempt in range(1, OPEN_ATTEMPTS + 1):
            try:
                with page.expect_response(lambda r: "token/generateToken" in r.url, timeout=60_000) as resp:
                    page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
                token = resp.value.json()["data"]["token"]
                break
            except Exception as e:
                if attempt == OPEN_ATTEMPTS:
                    raise ScraperError(f"could not open akasaair.com or get a guest token after {attempt} attempts: {e}") from e
                log.warning("Akasa: opening the site failed (attempt %d of %d), retrying: %s", attempt, OPEN_ATTEMPTS, str(e).splitlines()[0])
                polite_delay(*RETRY_WAIT_S)
        yield page, token


def _post(page, token: str, url: str, body: dict) -> dict:
    result = page.evaluate(_FETCH_JS, [url, token, body])
    if result["status"] != 200:
        raise ScraperError(f"{url.rsplit('/', 1)[-1]} returned HTTP {result['status']}")
    try:
        return json.loads(result["text"])
    except ValueError as e:
        raise ScraperError(f"unexpected response from {url}: {e}") from e


def fetch_low_fares(page, token: str, origin: str, destination: str, today: date) -> dict[date, float]:
    body = {
        "currencyCode": "INR",
        "origin": origin,
        "destination": destination,
        "startDate": today.isoformat(),
        "endDate": (today + timedelta(days=CALENDAR_DAYS)).isoformat(),
        "includeTaxesAndFees": True,
        "numberOfPassengers": 1,
    }
    return parse_low_fares(_post(page, token, LOW_FARE_URL, body))


def fetch_flight_search(page, token: str, origin: str, destination: str, departure: date) -> dict:
    """Every flight on `departure`, as the site's own search returns it (city-wide)."""
    body = {
        "criteria": [
            {
                "stations": {
                    "originStationCodes": [origin],
                    "destinationStationCodes": [destination],
                    "searchDestinationMacs": True,
                    "searchOriginMacs": True,
                },
                "dates": {"beginDate": f"{departure.isoformat()}T00:00:00"},
                "filters": {"compressionType": 1, "maxConnections": 8, "productClasses": ["NB", "LB", "EC", "AV"], "fareTypes": ["NB", "LB", "R", "V"]},
            }
        ],
        "passengers": {"types": [{"type": "ADT", "count": 1}], "residentCountry": ""},
        "codes": {"currencyCode": "INR", "promotionCode": ""},
        "offerCode": None,
        "numberOfFaresPerJourney": 10,
        "taxesAndFees": 1,
    }
    return _post(page, token, SEARCH_URL, body)


class AkasaScraper(Scraper):
    airline = "QP"
    name = "Akasa Air"
    source = "akasa_lowfare"

    def scrape(self, routes: list[tuple[str, str]], today: date) -> list[FareRow]:
        rows: list[FareRow] = []
        with akasa_session() as (page, token):
            for origin, destination in routes:
                polite_delay()
                try:
                    calendar = fetch_low_fares(page, token, origin, destination, today)
                except ScraperError as e:
                    log.warning("Akasa %s-%s: %s", origin, destination, e)
                    continue
                if not calendar:
                    log.info("Akasa %s-%s: no flights in the calendar (route not operated)", origin, destination)
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
                log.info("Akasa %s-%s: %d quotes", origin, destination, len(quotes))
                rows += quotes
        return rows
