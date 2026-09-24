"""Data freshness and scraper status for the dashboard header."""
import json

from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlmodel import Session, func, select

from app import db
from app.db import get_session
from app.models import Fare, IndexValue
from app.schemas import ScraperRunOut, StatusOut

router = APIRouter(prefix="/api", tags=["status"])

SYNTHETIC = "synthetic"


def last_scraper_run() -> ScraperRunOut | None:
    """The last batch report, or None if no batch has run (or the file is unreadable)."""
    try:
        return ScraperRunOut.model_validate(json.loads(db.SCRAPER_STATUS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError):
        return None


@router.get("/status", response_model=StatusOut)
def status(session: Session = Depends(get_session)) -> StatusOut:
    by_source = dict(session.exec(select(Fare.source, func.count()).group_by(Fare.source)).all())
    return StatusOut(
        latest_period=session.exec(select(func.max(IndexValue.period))).one(),
        fares_by_source=by_source,
        last_live_fare_at=session.exec(select(func.max(Fare.scrape_ts)).where(Fare.source != SYNTHETIC)).one(),
        last_run=last_scraper_run(),
    )
