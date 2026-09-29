"""Cross-check scraped prices against each airline's own flight search.

The scrapers read the airlines' low-fare calendars. This re-prices the same departure dates
through each airline's regular flight search (every flight on the date, full price) and checks
that the calendar price equals the cheapest flight between the same two airports.

  uv run python -m app.scraper.verify                                   # Akasa and SpiceJet, DEL-BOM and BLR-DEL
  uv run python -m app.scraper.verify --airline SG --route DEL-HYD

Per airline and route: 4 departure dates (Tuesday of each advance window), 2-5 s between
requests. Exit code 1 on any mismatch, 2 if a site could not be opened.
"""
import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from app.scraper import akasa, spicejet
from app.scraper.base import ScraperError, collection_plan, polite_delay, today_ist

DEFAULT_ROUTES = ["DEL-BOM", "BLR-DEL"]
TOLERANCE_INR = 1.0


@dataclass(frozen=True)
class Check:
    route: str
    departure: date
    window: int
    calendar: float | None  # what the scraper records
    cheapest_flight: float | None  # independent: cheapest flight, same airports, full search
    airline: str = "QP"

    @property
    def matches(self) -> bool:
        return self.calendar is not None and self.cheapest_flight is not None and abs(self.calendar - self.cheapest_flight) <= TOLERANCE_INR


def _tuesdays(today: date) -> list[tuple[int, date]]:
    return [(window, departure) for window, dow, departure in collection_plan(today) if dow == "TUE"]


def _search(search: Callable[[], float | None]) -> float | None:
    polite_delay()
    try:
        return search()
    except ScraperError:
        return None


def verify_akasa(routes: list[str], today: date) -> list[Check]:
    checks = []
    with akasa.akasa_session() as (page, token):
        for route in routes:
            origin, destination = route.split("-")
            polite_delay()
            calendar = akasa.fetch_low_fares(page, token, origin, destination, today)
            for window, departure in _tuesdays(today):
                cheapest = _search(lambda: akasa.cheapest_same_airports(akasa.fetch_flight_search(page, token, origin, destination, departure), origin, destination))
                checks.append(Check(route, departure, window, calendar.get(departure), cheapest, "QP"))
    return checks


def verify_spicejet(routes: list[str], today: date) -> list[Check]:
    checks = []
    with spicejet.spicejet_session() as (page, token):
        for route in routes:
            origin, destination = route.split("-")
            calendar: dict[date, float] = {}
            for centre in spicejet.calendar_centres(today):
                polite_delay()
                calendar |= spicejet.fetch_low_fares(page, token, origin, destination, centre)
            for window, departure in _tuesdays(today):
                cheapest = _search(lambda: spicejet.cheapest_same_airports(spicejet.fetch_flight_search(page, token, origin, destination, departure), origin, destination))
                checks.append(Check(route, departure, window, calendar.get(departure), cheapest, "SG"))
    return checks


VERIFIERS: dict[str, tuple[str, Callable[[list[str], date], list[Check]]]] = {
    "QP": ("Akasa Air", verify_akasa),
    "SG": ("SpiceJet", verify_spicejet),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check calendar prices against each airline's own flight search.")
    parser.add_argument("--airline", action="append", choices=sorted(VERIFIERS), help="default: all")
    parser.add_argument("--route", action="append", help="e.g. DEL-BOM (default: DEL-BOM and BLR-DEL)")
    args = parser.parse_args()
    fmt = lambda v: f"Rs {v:,.0f}" if v is not None else "n/a"  # noqa: E731

    checks: list[Check] = []
    failed_sites = []
    for code in args.airline or list(VERIFIERS):
        name, run = VERIFIERS[code]
        try:
            checks += run(args.route or DEFAULT_ROUTES, today_ist())
        except ScraperError as e:
            print(f"{name}: could not run the check: {e}")
            failed_sites.append(name)

    print(f"\n{'Airline':<9}{'Route':<9}{'Departure':<12}{'Window':<8}{'Scraped (calendar)':>20}{'Cheapest flight':>18}  Result")
    for c in checks:
        result = "MATCH" if c.matches else ("no flight" if c.calendar is None and c.cheapest_flight is None else "MISMATCH")
        print(f"{c.airline:<9}{c.route:<9}{c.departure.isoformat():<12}{f'{c.window}d':<8}{fmt(c.calendar):>20}{fmt(c.cheapest_flight):>18}  {result}")
    comparable = [c for c in checks if c.calendar is not None or c.cheapest_flight is not None]
    matched = sum(c.matches for c in comparable)
    print(f"\n{matched}/{len(comparable)} prices match the airline's own flight search (same airports, taxes included).")
    if failed_sites:
        sys.exit(2)
    sys.exit(0 if matched == len(comparable) else 1)


if __name__ == "__main__":
    main()
