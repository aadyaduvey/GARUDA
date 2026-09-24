"""Akasa Air scraper.

Loads akasaair.com in a headless browser, which issues the site's anonymous guest token,
then asks the site's own low-fare calendar endpoint for each route: one request returns
the lowest fare (taxes and fees included) for every departure date in the window.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

from app.scraper.base import ADVANCE_DAYS, FareRow, Scraper, ScraperError, browser_page, polite_delay, select_quotes

log = logging.getLogger("garuda.scraper.akasa")

HOME_URL = "https://www.akasaair.com/"
LOW_FARE_URL = "https://prod-bl.qp.akasaair.com/api/ibe/availability/search/lowFare"
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


class AkasaScraper(Scraper):
    airline = "QP"
    name = "Akasa Air"
    source = "akasa_lowfare"

    def scrape(self, routes: list[tuple[str, str]], today: date) -> list[FareRow]:
        rows: list[FareRow] = []
        with browser_page() as page:
            token = self._guest_token(page)
            for origin, destination in routes:
                polite_delay()
                try:
                    calendar = self._low_fares(page, token, origin, destination, today)
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

    def _guest_token(self, page) -> str:
        try:
            with page.expect_response(lambda r: "token/generateToken" in r.url, timeout=60_000) as resp:
                page.goto(HOME_URL, wait_until="domcontentloaded", timeout=60_000)
            return resp.value.json()["data"]["token"]
        except Exception as e:
            raise ScraperError(f"could not open akasaair.com or get a guest token: {e}") from e

    def _low_fares(self, page, token: str, origin: str, destination: str, today: date) -> dict[date, float]:
        body = {
            "currencyCode": "INR",
            "origin": origin,
            "destination": destination,
            "startDate": today.isoformat(),
            "endDate": (today + timedelta(days=CALENDAR_DAYS)).isoformat(),
            "includeTaxesAndFees": True,
            "numberOfPassengers": 1,
        }
        result = page.evaluate(_FETCH_JS, [LOW_FARE_URL, token, body])
        if result["status"] != 200:
            raise ScraperError(f"low-fare endpoint returned HTTP {result['status']}")
        try:
            return parse_low_fares(json.loads(result["text"]))
        except (ValueError, KeyError, TypeError) as e:
            raise ScraperError(f"unexpected low-fare response: {e}") from e
