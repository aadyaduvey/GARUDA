"""Compute route and national indices from the fares in the DB and write index_value rows.

Run after seeding:  uv run python -m app.build_index
"""
import pandas as pd
from sqlalchemy import Engine
from sqlmodel import Session, delete, select

from app.db import engine as default_engine
from app.engine.aggregate import national_series
from app.engine.anomaly import flag_anomalies
from app.engine.jevons import route_indices
from app.models import IST, Fare, IndexValue, Route
from app.pipeline.clean import drop_outliers
from app.pipeline.impute import carry_forward

BASE_DAYS = 7  # PoC base period: the first week of collected fares = 100


def load_fares(session: Session, route_id: int | None = None) -> pd.DataFrame:
    """All fares (or one route's) as a DataFrame with a `period` column. Empty if there are none."""
    query = select(Fare) if route_id is None else select(Fare).where(Fare.route_id == route_id)
    fares = pd.DataFrame([f.model_dump() for f in session.exec(query)])
    if fares.empty:
        return fares
    # Timestamps are stored in UTC; a fare's period is its IST calendar date.
    fares["period"] = pd.to_datetime(fares["scrape_ts"], utc=True).dt.tz_convert(IST).dt.date
    return fares


def build(eng: Engine = default_engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Recompute all index_value rows. Returns (route indices with anomaly flags, national series)."""
    with Session(eng) as session:
        fares = load_fares(session)
        if fares.empty:
            raise ValueError("no fares in the DB; run `uv run python -m app.seed` first")
        weights = {route.id: route.dgca_weight for route in session.exec(select(Route))}
        periods = sorted(fares["period"].unique())
        quotes = carry_forward(drop_outliers(fares), periods)
        routes = flag_anomalies(route_indices(quotes, periods[:BASE_DAYS]))
        national = national_series(routes, weights)

        session.exec(delete(IndexValue))
        session.add_all(
            IndexValue(
                route_id=int(row.route_id),
                period=row.period,
                jevons_index=float(row.jevons_index),
                anomaly_flag=bool(row.anomaly_flag),
            )
            for row in routes.itertuples()
        )
        session.add_all(
            IndexValue(period=row.period, national_index=float(row.national_index)) for row in national.itertuples()
        )
        session.commit()
    return routes, national


def main() -> None:
    routes, national = build()
    with Session(default_engine) as session:
        names = {r.id: f"{r.origin}-{r.destination}" for r in session.exec(select(Route))}

    latest = national.iloc[-1]
    print(f"National index on {latest.period}: {latest.national_index:.2f}  (base = first {BASE_DAYS} days = 100)\n")
    print("National series:")
    for row in national.itertuples():
        print(f"  {row.period}  {row.national_index:7.2f}")

    flagged = routes[routes["anomaly_flag"]]
    print(f"\nAnomaly flags (z > 2 and >= 5% rise vs preceding 7 days): {len(flagged)}")
    for row in flagged.itertuples():
        print(f"  {names[row.route_id]:<8} {row.period}  index {row.jevons_index:7.2f}  z = {row.z_score:.1f}")


if __name__ == "__main__":
    main()
