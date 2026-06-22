import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..models.recommendation_cache import RecommendationCache

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)


@router.get("/value-bets")
async def value_bets(
    min_ev: float = Query(0.05, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    """Return value bets from cache, falling back to live computation."""
    cached = (
        db.query(RecommendationCache)
        .filter(RecommendationCache.cache_type == "value_bets")
        .all()
    )

    valid_cache = [c for c in cached if not c.is_expired()]

    if not valid_cache:
        logger.info("Value bets cache miss — returning empty results")
        return {"matches": [], "total": 0, "page": page, "cached_at": datetime.utcnow().isoformat()}

    # 批量预加载所有涉及到的球队（避免 N+1 查询）
    codes_needed = {c.team_a_code for c in valid_cache} | {c.team_b_code for c in valid_cache}
    teams_by_code = {t.code: t for t in db.query(Team).filter(Team.code.in_(codes_needed)).all()}

    all_bets = []
    for c in valid_cache:
        recs = json.loads(c.result_data)
        team_a = teams_by_code.get(c.team_a_code)
        team_b = teams_by_code.get(c.team_b_code)
        if not team_a or not team_b:
            continue
        for rec in recs:
            if rec.get("ev", 0) >= min_ev:
                all_bets.append({
                    "team_a": team_a.name_cn or team_a.name,
                    "team_b": team_b.name_cn or team_b.name,
                    "team_a_code": team_a.code,
                    "team_b_code": team_b.code,
                    **rec,
                })

    all_bets.sort(key=lambda r: r.get("ev", 0), reverse=True)
    total = len(all_bets)
    start = (page - 1) * page_size
    latest_cached = max(c.computed_at for c in valid_cache)

    return {
        "matches": all_bets[start:start + page_size],
        "total": total,
        "page": page,
        "cached_at": latest_cached.isoformat(),
    }


async def _compute_value_bets_live(min_ev, page, page_size, db):
    logger.warning("_compute_value_bets_live called with no cache — returning empty (cache miss)")
    return {"matches": [], "total": 0, "page": page}


@router.get("/discrepancies")
async def discrepancies(
    min_delta: float = Query(0.12, ge=0.05),
    db: Session = Depends(get_db),
):
    """Return discrepancy alerts from cache, falling back to live computation."""
    cached = (
        db.query(RecommendationCache)
        .filter(RecommendationCache.cache_type == "discrepancies")
        .all()
    )

    valid_cache = [c for c in cached if not c.is_expired()]

    if not valid_cache:
        logger.info("Discrepancies cache miss — returning empty results")
        return {"alerts": [], "total": 0, "cached_at": datetime.utcnow().isoformat()}

    # 批量预加载所有涉及到的球队（避免 N+1 查询）
    codes_needed = {c.team_a_code for c in valid_cache} | {c.team_b_code for c in valid_cache}
    teams_by_code = {t.code: t for t in db.query(Team).filter(Team.code.in_(codes_needed)).all()}

    alerts = []
    for c in valid_cache:
        data = json.loads(c.result_data)
        if "discrepancy" in data:
            disc = data["discrepancy"]
            system_probs = data.get("system_probs", {})
            market_probs = data.get("market_probs")
        else:
            disc = data
            system_probs = {}
            market_probs = None
        if disc and disc.get("detected") and disc.get("max_delta", 0) >= min_delta:
            team_a = teams_by_code.get(c.team_a_code)
            team_b = teams_by_code.get(c.team_b_code)
            if team_a and team_b:
                alerts.append({
                    "team_a": team_a.name_cn or team_a.name,
                    "team_b": team_b.name_cn or team_b.name,
                    "team_a_code": team_a.code,
                    "team_b_code": team_b.code,
                    "group": team_a.group_name,
                    "discrepancy": disc,
                    "system_probs": system_probs,
                    "market_probs": market_probs,
                })

    latest_cached = max(c.computed_at for c in valid_cache)
    return {"alerts": alerts, "total": len(alerts), "cached_at": latest_cached.isoformat()}


async def _compute_discrepancies_live(min_delta, db):
    logger.warning("_compute_discrepancies_live called with no cache — returning empty (cache miss)")
    return {"alerts": [], "total": 0}
