"""Ingest scraped fare rows into the fare table: validate, map codes to ids, skip duplicates."""
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.models import Airline, Fare, Route
from app.scraper.base import ADVANCE_DAYS, DEP_DOWS, FareRow


@dataclass
class IngestResult:
    inserted: int = 0
    duplicates: int = 0
    rejected: Counter = field(default_factory=Counter)  # reason -> count


def ingest(session: Session, rows: Iterable[FareRow]) -> IngestResult:
    """Insert valid, new rows. Re-ingesting the same capture (e.g. a repeated --dry-run) is a no-op."""
    routes = {(r.origin, r.destination): r.id for r in session.exec(select(Route))}
    airlines = {a.code: a.id for a in session.exec(select(Airline))}
    result = IngestResult()
    for row in rows:
        reason = _rejection(row, routes, airlines)
        if reason:
            result.rejected[reason] += 1
            continue
        fare = Fare(
            route_id=routes[(row.origin, row.destination)],
            airline_id=airlines[row.airline],
            amount=row.amount,
            advance_days=row.advance_days,
            dep_dow=row.dep_dow,
            scrape_ts=row.scrape_ts,
            source=row.source,
        )
        if _exists(session, fare):
            result.duplicates += 1
            continue
        session.add(fare)
        result.inserted += 1
    session.commit()
    return result


def _rejection(row: FareRow, routes: dict, airlines: dict) -> str | None:
    if (row.origin, row.destination) not in routes:
        return f"route {row.origin}-{row.destination} not in basket"
    if row.airline not in airlines:
        return f"airline {row.airline} unknown"
    if row.advance_days not in ADVANCE_DAYS or row.dep_dow not in DEP_DOWS:
        return "not a collection-spec quote"
    if row.amount <= 0:
        return "non-positive fare"
    return None


def _exists(session: Session, fare: Fare) -> bool:
    return (
        session.exec(
            select(Fare.id).where(
                Fare.route_id == fare.route_id,
                Fare.airline_id == fare.airline_id,
                Fare.advance_days == fare.advance_days,
                Fare.dep_dow == fare.dep_dow,
                Fare.scrape_ts == fare.scrape_ts,
                Fare.source == fare.source,
            )
        ).first()
        is not None
    )
