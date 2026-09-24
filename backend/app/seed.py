"""Synthetic fare generator: realistic yield curve, daily noise, one planted anomaly.

Wipe the DB and reseed:  uv run python -m app.seed
"""
import argparse
import csv
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import Engine
from sqlmodel import Session, func, select

from app.db import DATA_DIR, engine as default_engine, reset_db
from app.models import IST, Airline, Fare, IndexValue, Route

ROUTE_BASKET_CSV = DATA_DIR / "route_basket.csv"

N_DAYS = 14
ADVANCE_DAYS = (1, 7, 14, 30)
DEP_DOWS = ("TUE", "SAT")

# (name, IATA code, domestic market-share proxy, price level relative to IndiGo)
AIRLINES = [
    ("IndiGo", "6E", 0.64, 1.00),
    ("Air India", "AI", 0.27, 1.08),
    ("Akasa Air", "QP", 0.05, 0.96),
]

# Typical 30-day-advance economy fare (INR) for IndiGo on a Tuesday.
BASE_FARES = {
    ("DEL", "BOM"): 4800,
    ("BOM", "DEL"): 4700,
    ("DEL", "BLR"): 5600,
    ("BLR", "DEL"): 5500,
    ("DEL", "HYD"): 4900,
    ("BOM", "BLR"): 3600,
    ("DEL", "CCU"): 5200,
    ("BOM", "GOI"): 3200,
    ("BLR", "PNQ"): 3400,
    ("DEL", "MAA"): 5800,
}

# Yield curve: 30d cheapest, rising through 14d and 7d, steep at 1d.
YIELD_MULTIPLIER = {30: 1.00, 14: 1.12, 7: 1.35, 1: 2.10}
DOW_MULTIPLIER = {"TUE": 0.96, "SAT": 1.06}
NOISE_SIGMA = 0.04  # daily log-normal noise per quote

ANOMALY_ROUTE = ("DEL", "BOM")
ANOMALY_DAY = 10  # 1-based day of the seeded window
ANOMALY_FACTOR = 1.6


def load_routes(path: Path = ROUTE_BASKET_CSV) -> list[Route]:
    with open(path, newline="") as f:
        return [
            Route(origin=row["origin"], destination=row["destination"], dgca_weight=float(row["dgca_weight"]))
            for row in csv.DictReader(f)
        ]


def generate_fares(routes: list[Route], airlines: list[Airline], start: date, rng: np.random.Generator) -> list[Fare]:
    price_level = {code: level for _, code, _, level in AIRLINES}
    fares = []
    for day in range(N_DAYS):
        scrape_ts = datetime.combine(start + timedelta(days=day), time(6, 0), tzinfo=IST)
        for route in routes:
            key = (route.origin, route.destination)
            spike = ANOMALY_FACTOR if key == ANOMALY_ROUTE and day == ANOMALY_DAY - 1 else 1.0
            for airline in airlines:
                for advance in ADVANCE_DAYS:
                    for dow in DEP_DOWS:
                        amount = (
                            BASE_FARES[key]
                            * price_level[airline.code]
                            * YIELD_MULTIPLIER[advance]
                            * DOW_MULTIPLIER[dow]
                            * spike
                            * rng.lognormal(0.0, NOISE_SIGMA)
                        )
                        fares.append(
                            Fare(
                                route_id=route.id,
                                airline_id=airline.id,
                                amount=float(round(amount)),
                                advance_days=advance,
                                dep_dow=dow,
                                scrape_ts=scrape_ts,
                                source="synthetic",
                            )
                        )
    return fares


def seed(eng: Engine = default_engine, start: date | None = None, rng_seed: int = 42) -> dict[str, int]:
    """Wipe all tables and insert routes, airlines and N_DAYS of synthetic fares. Returns row counts."""
    start = start or date.today() - timedelta(days=N_DAYS - 1)
    reset_db(eng)
    with Session(eng) as session:
        routes = load_routes()
        airlines = [Airline(name=name, code=code, market_share=share) for name, code, share, _ in AIRLINES]
        session.add_all(routes + airlines)
        session.flush()
        session.add_all(generate_fares(routes, airlines, start, np.random.default_rng(rng_seed)))
        session.commit()
        return {
            model.__tablename__: session.exec(select(func.count()).select_from(model)).one()
            for model in (Route, Airline, Fare, IndexValue)
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Wipe the GARUDA DB and reseed synthetic fares.")
    parser.add_argument("--start", type=date.fromisoformat, help="first seeded day, YYYY-MM-DD (default: 13 days ago)")
    parser.add_argument("--rng-seed", type=int, default=42)
    args = parser.parse_args()
    for table, count in seed(start=args.start, rng_seed=args.rng_seed).items():
        print(f"{table:<12} {count:>6}")


if __name__ == "__main__":
    main()
