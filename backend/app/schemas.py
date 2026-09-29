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


class OfficialPoint(BaseModel):
    month: str  # "YYYY-MM"
    index: float  # base 2024 = 100
    inflation: float | None  # % vs the same month a year earlier, as published


class OfficialLink(BaseModel):
    month: str  # the overlapping month used to chain-link GARUDA to the official series
    garuda_days: int
    factor: float
    latest_period: date
    latest_value: float  # GARUDA's latest national index on the official 2024 = 100 scale


class OfficialOut(BaseModel):
    available: bool  # False until the series has been downloaded once
    item: str  # "Airfare"
    code: str  # CPI item code, e.g. "07.3.3.1.2.01"
    base_year: str
    area: str
    source_name: str
    source_url: str
    fetched_at: datetime | None
    series: list[OfficialPoint]
    link: OfficialLink | None  # None until GARUDA has LINK_MIN_DAYS days in a published month
    link_min_days: int
