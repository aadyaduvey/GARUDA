"""Cross-check scraped prices against Akasa's own flight search.

The scraper reads Akasa's low-fare calendar. This re-prices the same departure dates through
Akasa's regular flight search (every flight on the date, full price) and checks that the
calendar price equals the cheapest flight between the same two airports.

  uv run python -m app.scraper.verify                                  # DEL-BOM and BLR-DEL
  uv run python -m app.scraper.verify --route DEL-HYD --route BOM-BLR

Uses 5 requests per route (1 calendar + 4 departure dates), 2-5 s apart. Exit code 1 on any mismatch.
"""
import argparse
import sys
from dataclasses import dataclass
from datetime import date

from app.scraper.akasa import akasa_session, cheapest_same_airports, fetch_flight_search, fetch_low_fares
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

    @property
    def matches(self) -> bool:
        return self.calendar is not None and self.cheapest_flight is not None and abs(self.calendar - self.cheapest_flight) <= TOLERANCE_INR


def verify(routes: list[str], today: date) -> list[Check]:
    """Tuesday departures for each advance window, per route."""
    checks = []
    with akasa_session() as (page, token):
        for route in routes:
            origin, destination = route.split("-")
            polite_delay()
            calendar = fetch_low_fares(page, token, origin, destination, today)
            for window, _, departure in (q for q in collection_plan(today) if q[1] == "TUE"):
                polite_delay()
                try:
                    cheapest = cheapest_same_airports(fetch_flight_search(page, token, origin, destination, departure), origin, destination)
                except ScraperError:
                    cheapest = None
                checks.append(Check(route, departure, window, calendar.get(departure), cheapest))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-check Akasa calendar prices against Akasa's flight search.")
    parser.add_argument("--route", action="append", help="e.g. DEL-BOM (default: DEL-BOM and BLR-DEL)")
    args = parser.parse_args()
    fmt = lambda v: f"Rs {v:,.0f}" if v is not None else "n/a"  # noqa: E731

    try:
        checks = verify(args.route or DEFAULT_ROUTES, today_ist())
    except ScraperError as e:
        print(f"Could not run the check: {e}")
        sys.exit(2)

    print(f"\n{'Route':<9}{'Departure':<12}{'Window':<8}{'Scraped (calendar)':>20}{'Cheapest flight':>18}  Result")
    for c in checks:
        print(f"{c.route:<9}{c.departure.isoformat():<12}{f'{c.window}d':<8}{fmt(c.calendar):>20}{fmt(c.cheapest_flight):>18}  {'MATCH' if c.matches else 'MISMATCH'}")
    matched = sum(c.matches for c in checks)
    print(f"\n{matched}/{len(checks)} prices match Akasa's own flight search (same airports, taxes included).")
    sys.exit(0 if matched == len(checks) else 1)


if __name__ == "__main__":
    main()
