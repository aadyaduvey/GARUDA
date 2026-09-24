"""Helpers shared by the route modules."""
from fastapi import HTTPException
from sqlmodel import Session, select

from app.build_index import BASE_DAYS
from app.models import IndexValue, Route
from app.schemas import BasePeriod, RouteOut


def route_label(route: Route) -> str:
    return f"{route.origin}-{route.destination}"


def route_out(route: Route) -> RouteOut:
    return RouteOut(
        id=route.id, origin=route.origin, destination=route.destination, label=route_label(route), dgca_weight=route.dgca_weight
    )


def get_route_or_404(session: Session, route_id: int) -> Route:
    route = session.get(Route, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"route {route_id} not found")
    return route


def base_period(session: Session) -> BasePeriod | None:
    """The index base: the first BASE_DAYS periods of the national series (= 100)."""
    periods = session.exec(
        select(IndexValue.period).where(IndexValue.route_id.is_(None)).order_by(IndexValue.period).limit(BASE_DAYS)
    ).all()
    return BasePeriod(start=periods[0], end=periods[-1]) if periods else None
