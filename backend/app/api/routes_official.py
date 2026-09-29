"""The official MoSPI CPI airfare index, and GARUDA chain-linked to it where the two overlap."""
from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app import official
from app.db import get_session
from app.models import IndexValue
from app.schemas import OfficialLink, OfficialOut, OfficialPoint

router = APIRouter(prefix="/api", tags=["official"])


@router.get("/official/cpi-airfare", response_model=OfficialOut)
def cpi_airfare(session: Session = Depends(get_session)) -> OfficialOut:
    doc = official.load(official.CACHE_FILE)
    series = doc["series"] if doc else []
    national = session.exec(select(IndexValue.period, IndexValue.national_index).where(IndexValue.route_id.is_(None))).all()
    link = official.link_to_official([(p, v) for p, v in national], series)
    return OfficialOut(
        available=doc is not None,
        item=official.ITEM["name"],
        code=official.ITEM["code"],
        base_year=official.ITEM["base_year"],
        area=official.ITEM["area"],
        source_name=doc["source"]["name"] if doc else "MoSPI eSankhyiki, CPI (base 2024)",
        source_url=official.PORTAL_URL,
        fetched_at=doc["fetched_at"] if doc else None,
        series=[OfficialPoint(**p) for p in series],
        link=OfficialLink(**asdict(link)) if link else None,
        link_min_days=official.LINK_MIN_DAYS,
    )
