"""Pydantic response models. The API never returns raw ORM objects."""
from datetime import date, datetime

from pydantic import BaseModel


class RouteOut(BaseModel):
    id: int
    origin: str
    destination: str
    label: str  # e.g. "DEL-BOM"
    dgca_weight: float


class BasePeriod(BaseModel):
    start: date
    end: date


class NationalPoint(BaseModel):
    period: date
    national_index: float


class NationalIndexOut(BaseModel):
    base_period: BasePeriod | None
    latest: NationalPoint | None
    series: list[NationalPoint]


class RoutePoint(BaseModel):
    period: date
    jevons_index: float
    anomaly_flag: bool


class CarrierOut(BaseModel):
    airline: str
    code: str
    market_share: float
    avg_fare: float  # mean fare in the latest period, all windows and days


class RouteIndexOut(BaseModel):
    route: RouteOut
    base_period: BasePeriod | None
    series: list[RoutePoint]
    carriers: list[CarrierOut]


class FareOut(BaseModel):
    id: int
    route_id: int
    route: str
    airline_code: str
    amount: float
    advance_days: int
    dep_dow: str
    scrape_ts: datetime
    source: str
    imputed: bool


class AnomalyOut(BaseModel):
    route_id: int
    route: str
    period: date
    jevons_index: float
    z_score: float
    rise_pct: float  # % above the preceding 7-day mean
    severity: str  # "low" | "medium" | "high"


class YieldPoint(BaseModel):
    period: date
    advance_days: int
    avg_fare: float


class YieldCurveOut(BaseModel):
    route: RouteOut
    premium_1d_vs_30d: float | None  # mean 1-day fare / mean 30-day fare
    series: list[YieldPoint]


class SourceStatusOut(BaseModel):
    airline: str
    name: str
    status: str  # "ok" | "no_data" | "failed" | "unavailable"
    rows: int
    inserted: int
    error: str | None


class ScraperRunOut(BaseModel):
    run_at: datetime
    mode: str  # "live" | "dry_run"
    index_rebuilt: bool
    sources: list[SourceStatusOut]


class StatusOut(BaseModel):
    dataset: str  # "demo" | "live"
    first_period: date | None
    latest_period: date | None
    days_collected: int  # periods with a national index value
    base_days: int  # periods that form the base (= 100); the index is provisional until reached
    fares_by_source: dict[str, int]
    last_live_fare_at: datetime | None  # newest non-synthetic fare
    last_run: ScraperRunOut | None
