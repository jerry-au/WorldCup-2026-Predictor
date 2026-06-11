from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.match_aggregator import build_today_matches_response

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/today")
def today_matches(
    target_date: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    return build_today_matches_response(db=db, target_date=target_date)
