"""Fare, anomaly and yield-curve endpoints."""
from datetime import date, datetime, time, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.common import get_route_or_404, route_label, route_out
from app.build_index import load_fares
from app.db import get_session
from app.engine.anomaly import flag_anomalies, severity
from app.engine.yield_curve import advance_premium, yield_curve
from app.models import IST, Airline, Fare, IndexValue, Route
from app.pipeline.clean import drop_outliers
from app.schemas import AnomalyOut, FareOut, YieldCurveOut, YieldPoint

router = APIRouter(prefix="/api", tags=["fares"])


@router.get("/fares", response_model=list[FareOut])
def list_fares(
    route_id: int | None = None,
    airline: str | None = Query(None, description="IATA code, e.g. 6E"),
    advance_days: int | None = None,
    dep_dow: str | None = Query(None, description="TUE or SAT"),
    start: date | None = Query(None, description="first IST collection date, inclusive"),
    end: date | None = Query(None, description="last IST collection date, inclusive"),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[FareOut]:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    query = select(Fare, Route, Airline).join(Route).join(Airline)
    if route_id is not None:
        query = query.where(Fare.route_id == route_id)
    if airline is not None:
        query = query.where(Airline.code == airline.upper())
    if advance_days is not None:
        query = query.where(Fare.advance_days == advance_days)
    if dep_dow is not None:
        query = query.where(Fare.dep_dow == dep_dow.upper())
    if start is not None:
        query = query.where(Fare.scrape_ts >= datetime.combine(start, time.min, tzinfo=IST))
    if end is not None:
        query = query.where(Fare.scrape_ts < datetime.combine(end + timedelta(days=1), time.min, tzinfo=IST))
    rows = session.exec(query.order_by(Fare.scrape_ts, Fare.id).offset(offset).limit(limit)).all()
    return [
        FareOut(**fare.model_dump(exclude={"airline_id"}), route=route_label(route), airline_code=al.code)
        for fare, route, al in rows
    ]


@router.get("/anomalies", response_model=list[AnomalyOut])
def list_anomalies(session: Session = Depends(get_session)) -> list[AnomalyOut]:
    """Flagged route-days, newest first. z-scores are recomputed from the stored route index series."""
    rows = session.exec(select(IndexValue).where(IndexValue.route_id.is_not(None))).all()
    if not rows:
        return []
    series = pd.DataFrame([{"route_id": r.route_id, "period": r.period, "jevons_index": r.jevons_index} for r in rows])
    flagged = flag_anomalies(series).query("anomaly_flag").sort_values("period", ascending=False)
    labels = {r.id: route_label(r) for r in session.exec(select(Route))}
    return [
        AnomalyOut(
            route_id=row.route_id,
            route=labels[row.route_id],
            period=row.period,
            jevons_index=round(row.jevons_index, 2),
            z_score=round(row.z_score, 2),
            rise_pct=round(row.rise * 100, 1),
            severity=severity(row.rise),
        )
        for row in flagged.itertuples()
    ]


@router.get("/yield-curve/{route_id}", response_model=YieldCurveOut)
def route_yield_curve(route_id: int, session: Session = Depends(get_session)) -> YieldCurveOut:
    route = get_route_or_404(session, route_id)
    fares = load_fares(session, route_id)
    if fares.empty:
        return YieldCurveOut(route=route_out(route), premium_1d_vs_30d=None, series=[])
    fares = drop_outliers(fares)
    return YieldCurveOut(
        route=route_out(route),
        premium_1d_vs_30d=round(advance_premium(fares), 3),
        series=[YieldPoint(period=r.period, advance_days=r.advance_days, avg_fare=round(r.avg_fare, 2)) for r in yield_curve(fares).itertuples()],
    )
