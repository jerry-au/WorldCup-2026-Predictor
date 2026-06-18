import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..models.recommendation_cache import RecommendationCache
from ..core.prediction import PredictionEngine
from ..services.odds import odds_client
from ..services.recommendation import recommendation_engine

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])
engine = PredictionEngine()


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
        return await _compute_value_bets_live(min_ev, page, page_size, db)

    all_bets = []
    for c in valid_cache:
        recs = json.loads(c.result_data)
        for rec in recs:
            if rec.get("ev", 0) >= min_ev:
                team_a = db.query(Team).filter(Team.code == c.team_a_code).first()
                team_b = db.query(Team).filter(Team.code == c.team_b_code).first()
                if team_a and team_b:
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
    """Original live computation logic as fallback."""
    teams = db.query(Team).all()
    predicted = []
    scanned = 0

    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if j <= i or team_a.group_name != team_b.group_name:
                continue

            pred = engine.predict(team_a, team_b, db=db, match_type="group")
            odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
            betting = recommendation_engine.analyze(
                system_probs=pred["probabilities"],
                system_confidence=pred["system_confidence"],
                odds_data=odds_data,
            )

            if betting["recommendations"]:
                for rec in betting["recommendations"]:
                    if rec["ev"] >= min_ev:
                        predicted.append({
                            "team_a": team_a.name_cn or team_a.name,
                            "team_b": team_b.name_cn or team_b.name,
                            "team_a_code": team_a.code,
                            "team_b_code": team_b.code,
                            **rec,
                        })
            scanned += 1

    predicted.sort(key=lambda r: r["ev"], reverse=True)
    total = len(predicted)
    start = (page - 1) * page_size
    return {"matches": predicted[start:start + page_size], "total": total, "page": page}


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
        return await _compute_discrepancies_live(min_delta, db)

    alerts = []
    for c in valid_cache:
        data = json.loads(c.result_data)
        # 兼容新旧两种缓存格式
        if "discrepancy" in data:
            disc = data["discrepancy"]
            system_probs = data.get("system_probs", {})
            market_probs = data.get("market_probs")
        else:
            disc = data
            system_probs = {}
            market_probs = None
        if disc and disc.get("detected") and disc.get("max_delta", 0) >= min_delta:
            team_a = db.query(Team).filter(Team.code == c.team_a_code).first()
            team_b = db.query(Team).filter(Team.code == c.team_b_code).first()
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
    """Original live computation logic as fallback."""
    teams = db.query(Team).all()
    alerts = []
    scanned = 0

    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if j <= i or team_a.group_name != team_b.group_name:
                continue

            pred = engine.predict(team_a, team_b, db=db, match_type="group")
            odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
            betting = recommendation_engine.analyze(
                system_probs=pred["probabilities"],
                system_confidence=pred["system_confidence"],
                odds_data=odds_data,
            )
            if betting["discrepancy"] and betting["discrepancy"].get("detected") and betting["discrepancy"].get("max_delta", 0) >= min_delta:
                alerts.append({
                    "team_a": team_a.name_cn or team_a.name,
                    "team_b": team_b.name_cn or team_b.name,
                    "team_a_code": team_a.code,
                    "team_b_code": team_b.code,
                    "group": team_a.group_name,
                    "discrepancy": betting["discrepancy"],
                    "system_probs": pred["probabilities"],
                    "market_probs": betting.get("odds_comparison", {}).get("market_implied", {}),
                })
            scanned += 1

    return {"alerts": alerts, "total": len(alerts)}
