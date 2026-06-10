from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..schemas.predict import PredictRequest, PredictResponse
from ..core.prediction import PredictionEngine
from ..services.odds import odds_client
from ..services.recommendation import recommendation_engine

router = APIRouter(prefix="/api/v1/predict", tags=["predict"])
engine = PredictionEngine()


@router.post("/match", response_model=PredictResponse)
async def predict_match(body: PredictRequest, db: Session = Depends(get_db)):
    team_a = db.query(Team).filter(Team.code == body.team_a_code.upper()).first()
    team_b = db.query(Team).filter(Team.code == body.team_b_code.upper()).first()

    if not team_a:
        raise HTTPException(404, detail={"code": 1001, "message": f"Team {body.team_a_code} not found"})
    if not team_b:
        raise HTTPException(404, detail={"code": 1001, "message": f"Team {body.team_b_code} not found"})
    if team_a.code == team_b.code:
        raise HTTPException(400, detail={"code": 1003, "message": "Cannot predict same team"})

    # System prediction
    prediction = engine.predict(team_a, team_b, body.match_type)

    # Fetch odds and generate recommendations
    odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
    betting = recommendation_engine.analyze(
        system_probs=prediction["probabilities"],
        system_confidence=prediction["system_confidence"],
        odds_data=odds_data,
    )

    prediction["betting"] = betting
    return prediction
