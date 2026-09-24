"""CPI CSV export: route, period, index_value, weight, base_period."""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session, select

from app.api.common import base_period, route_label
from app.db import get_session
from app.models import IndexValue, Route

router = APIRouter(prefix="/api/export", tags=["export"])

CSV_COLUMNS = ["route", "period", "index_value", "weight", "base_period"]
NATIONAL_LABEL = "NATIONAL"


@router.get("/cpi", response_class=Response, responses={200: {"content": {"text/csv": {}}}})
def export_cpi(
    start: date | None = Query(None, description="first period, inclusive"),
    end: date | None = Query(None, description="last period, inclusive"),
    session: Session = Depends(get_session),
) -> Response:
    """Route rows then the national row for each period. An empty range returns the header only."""
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="start must be on or before end")
    query = select(IndexValue, Route).join(Route, isouter=True)
    if start is not None:
        query = query.where(IndexValue.period >= start)
    if end is not None:
        query = query.where(IndexValue.period <= end)
    # Within a period: routes by weight (largest first), national row last.
    rows = session.exec(query.order_by(IndexValue.period, IndexValue.route_id.is_(None), Route.dgca_weight.desc())).all()

    base = base_period(session)
    base_label = f"{base.start}/{base.end}" if base else ""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for iv, route in rows:
        if route is None:
            writer.writerow([NATIONAL_LABEL, iv.period, f"{iv.national_index:.2f}", "1.00", base_label])
        else:
            writer.writerow([route_label(route), iv.period, f"{iv.jevons_index:.2f}", f"{route.dgca_weight:.2f}", base_label])

    filename = f"garuda_cpi_{start or 'all'}_{end or 'all'}.csv"
    return Response(
        buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
