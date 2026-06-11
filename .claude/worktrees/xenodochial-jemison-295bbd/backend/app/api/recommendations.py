from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
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
    """Scan select fixtures for value betting opportunities."""
    # In P0, we scan a subset of high-profile matchups rather than all 104
    # This avoids hitting The Odds API rate limit (500 req/month)
    teams = db.query(Team).all()
    predicted = []

    # Pick representative matchups per group (1-2 pairs)
    scanned = 0
    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if j <= i:
                continue
            if team_a.group_name != team_b.group_name:
                continue  # Only scan same-group matches in P0
            if scanned >= 12:  # One per group
                break

            pred = engine.predict(team_a, team_b, "group")
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
                            "team_a": pred["team_a"]["name"],
                            "team_b": pred["team_b"]["name"],
                            **rec,
                        })
            scanned += 1
        if scanned >= 12:
            break

    predicted.sort(key=lambda r: r["ev"], reverse=True)
    total = len(predicted)
    start = (page - 1) * page_size
    return {"matches": predicted[start:start+page_size], "total": total, "page": page}


@router.get("/discrepancies")
async def discrepancies(
    min_delta: float = Query(0.12, ge=0.05),
    db: Session = Depends(get_db),
):
    """List matches where system prediction differs significantly from market odds."""
    teams = db.query(Team).all()
    alerts = []

    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if j <= i or team_a.group_name != team_b.group_name:
                continue
            pred = engine.predict(team_a, team_b, "group")
            odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
            betting = recommendation_engine.analyze(
                system_probs=pred["probabilities"],
                system_confidence=pred["system_confidence"],
                odds_data=odds_data,
            )
            if betting["discrepancy"] and betting["discrepancy"].get("detected"):
                alerts.append({
                    "team_a": pred["team_a"]["name"],
                    "team_b": pred["team_b"]["name"],
                    "group": team_a.group_name,
                    "discrepancy": betting["discrepancy"],
                    "system_probs": pred["probabilities"],
                    "market_probs": betting.get("odds_comparison", {}).get("market_implied", {}),
                })

    return {"alerts": alerts, "total": len(alerts)}
