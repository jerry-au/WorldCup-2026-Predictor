from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.match_aggregator import build_odds_history_response, build_today_matches_response, build_all_matches_response

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/today")
def today_matches(
    target_date: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    return build_today_matches_response(db=db, target_date=target_date)


@router.get("/all")
def all_matches(
    stage: str | None = Query(None, description="Filter by stage: group_stage, round_of_16, quarter, semi, final"),
    status: str | None = Query(None, description="Filter by status: completed, upcoming, live"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
):
    """获取所有比赛赛程，包括已结束比赛的比分（支持分页）"""
    return build_all_matches_response(db=db, stage=stage, status=status, page=page, page_size=page_size)


# 注意：动态路由必须放在静态路由之后
@router.get("/{match_id}/odds-history")
def odds_history(
    match_id: str,
    home_code: str = Query(...),
    away_code: str = Query(...),
    db: Session = Depends(get_db),
):
    return build_odds_history_response(db, match_id, home_code, away_code)
