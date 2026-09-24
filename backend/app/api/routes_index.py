"""National and route index endpoints."""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.common import base_period, get_route_or_404, route_out
from app.build_index import load_fares
from app.db import get_session
from app.models import Airline, IndexValue, Route
from app.pipeline.clean import drop_outliers
from app.schemas import CarrierOut, NationalIndexOut, NationalPoint, RouteIndexOut, RouteOut, RoutePoint

router = APIRouter(prefix="/api", tags=["index"])


@router.get("/routes", response_model=list[RouteOut])
def list_routes(session: Session = Depends(get_session)) -> list[RouteOut]:
    return [route_out(r) for r in session.exec(select(Route).order_by(Route.dgca_weight.desc()))]


@router.get("/index/national", response_model=NationalIndexOut)
def national(session: Session = Depends(get_session)) -> NationalIndexOut:
    rows = session.exec(select(IndexValue).where(IndexValue.route_id.is_(None)).order_by(IndexValue.period)).all()
    series = [NationalPoint(period=r.period, national_index=r.national_index) for r in rows]
    return NationalIndexOut(base_period=base_period(session), latest=series[-1] if series else None, series=series)


@router.get("/index/route/{route_id}", response_model=RouteIndexOut)
def route_index(route_id: int, session: Session = Depends(get_session)) -> RouteIndexOut:
    route = get_route_or_404(session, route_id)
    rows = session.exec(select(IndexValue).where(IndexValue.route_id == route_id).order_by(IndexValue.period)).all()
    return RouteIndexOut(
        route=route_out(route),
        base_period=base_period(session),
        series=[RoutePoint(period=r.period, jevons_index=r.jevons_index, anomaly_flag=r.anomaly_flag) for r in rows],
        carriers=carrier_breakdown(session, route_id),
    )


def carrier_breakdown(session: Session, route_id: int) -> list[CarrierOut]:
    """Mean fare per airline on the route in the latest period."""
    fares = load_fares(session, route_id)
    if fares.empty:
        return []
    fares = drop_outliers(fares)
    latest = fares[fares["period"] == fares["period"].max()]
    avg = latest.groupby("airline_id")["amount"].mean()
    airlines = session.exec(select(Airline).where(Airline.id.in_(avg.index.tolist()))).all()
    return sorted(
        (CarrierOut(airline=a.name, code=a.code, market_share=a.market_share, avg_fare=round(avg[a.id], 2)) for a in airlines),
        key=lambda c: c.market_share,
        reverse=True,
    )
