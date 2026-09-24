"""SQLModel tables. Mirrors the canonical data model in CLAUDE.md."""
from datetime import date, datetime

from sqlmodel import Field, SQLModel


class Route(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    origin: str = Field(max_length=3)
    destination: str = Field(max_length=3)
    dgca_weight: float  # share of basket passenger traffic; basket sums to 1.0


class Airline(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    code: str = Field(max_length=2, unique=True)  # IATA code
    market_share: float


class Fare(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    route_id: int = Field(foreign_key="route.id", index=True)
    airline_id: int = Field(foreign_key="airline.id", index=True)
    amount: float  # INR, economy, lowest available
    advance_days: int  # 1, 7, 14 or 30
    dep_dow: str  # "TUE" or "SAT"
    scrape_ts: datetime = Field(index=True)
    source: str  # "synthetic", "pre_collected", or a scraper name
    imputed: bool = False


class IndexValue(SQLModel, table=True):
    __tablename__ = "index_value"

    id: int | None = Field(default=None, primary_key=True)
    route_id: int | None = Field(default=None, foreign_key="route.id", index=True)  # None = national row
    period: date = Field(index=True)
    jevons_index: float | None = None
    national_index: float | None = None
    anomaly_flag: bool = False
