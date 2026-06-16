import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..models.simulation import SimulationRun, SimulationResult, KnockoutBracket
from ..schemas.predict import (
    PredictRequest,
    PredictResponse,
    TournamentResponse,
    TaskProgressResponse,
)
from ..core.prediction import PredictionEngine
from ..core.simulation import MonteCarloEngine, TeamInGroup
from ..core.elo import composite_rating, get_team_dongqiudi_strength, get_team_market_value
from ..services.odds import odds_client
from ..services.recommendation import recommendation_engine

router = APIRouter(prefix="/api/v1/predict", tags=["predict"])
engine = PredictionEngine()

# ── In-memory task registry for simulation progress ──
_task_registry: dict[str, dict] = {}


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

    prediction = engine.predict(team_a, team_b, db, body.match_type)

    try:
        odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
    except Exception:
        odds_data = None

    betting = recommendation_engine.analyze(
        system_probs=prediction["probabilities"],
        system_confidence=prediction["system_confidence"],
        odds_data=odds_data,
    )

    prediction["betting"] = betting
    return prediction


# ── Tournament Simulation ──────────────────────────────────────────


@router.post("/tournament", response_model=TournamentResponse)
def start_tournament_simulation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start Monte Carlo tournament simulation (background task)."""
    run_id = str(uuid.uuid4())
    run = SimulationRun(id=run_id, status="running")
    db.add(run)
    db.commit()

    _task_registry[run_id] = {"status": "running", "progress": 0.0}

    background_tasks.add_task(_run_simulation, run_id)

    return TournamentResponse(task_id=run_id, status="running")


def _run_simulation(task_id: str):
    """Run simulation in background thread."""
    db = next(get_db())
    try:
        teams = db.query(Team).all()

        # Build input data
        groups: dict[str, list[TeamInGroup]] = {}
        team_names: dict[str, str] = {}

        for t in teams:
            strength = get_team_dongqiudi_strength(db, t)
            mv = get_team_market_value(db, t)
            groups.setdefault(t.group_name, []).append(
                TeamInGroup(
                    code=t.code,
                    group=t.group_name,
                    composite=composite_rating(elo=t.elo_rating, dongqiudi_strength=strength, market_value_eur=mv),
                )
            )
            team_names[t.code] = t.name_cn or t.name

        _task_registry[task_id]["progress"] = 0.1

        # Run simulation
        engine = MonteCarloEngine()
        results = engine.simulate(groups, team_names)

        _task_registry[task_id]["progress"] = 0.8

        # Save results
        for i, code in enumerate(results.team_codes):
            sr = SimulationResult(
                run_id=task_id,
                team_code=code,
                team_name=results.team_names[i],
                round_32=round(float(results.round_32[i]), 4),
                round_16=round(float(results.round_16[i]), 4),
                quarter=round(float(results.quarter[i]), 4),
                semi=round(float(results.semi[i]), 4),
                final_=round(float(results.final_[i]), 4),
                champion=round(float(results.champion[i]), 4),
            )
            db.add(sr)

        # Save bracket data
        for slot in results.bracket:
            kb = KnockoutBracket(
                run_id=task_id,
                round_name=slot.round_name,
                position=slot.position,
                team_a_code=slot.team_a,
                team_b_code=slot.team_b,
                prob_a=slot.prob_a,
                prob_b=slot.prob_b,
            )
            db.add(kb)

        run = db.query(SimulationRun).filter(SimulationRun.id == task_id).first()
        if run:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
        db.commit()

        _task_registry[task_id] = {"status": "completed", "progress": 1.0}

    except Exception as e:
        run = db.query(SimulationRun).filter(SimulationRun.id == task_id).first()
        if run:
            run.status = "failed"
            run.error = str(e)
            db.commit()
        _task_registry[task_id] = {"status": "failed", "progress": 0.0, "error": str(e)}
    finally:
        db.close()


@router.get("/task/{task_id}", response_model=TaskProgressResponse)
def get_task_progress(task_id: str, db: Session = Depends(get_db)):
    """Poll simulation progress or fetch completed results."""
    task = _task_registry.get(task_id)
    if not task:
        raise HTTPException(404, detail={"code": 2001, "message": "Task not found"})

    if task["status"] == "running":
        return TaskProgressResponse(
            status="running",
            progress=task.get("progress", 0.0),
        )

    if task["status"] == "failed":
        return TaskProgressResponse(
            status="failed",
            progress=0.0,
            error=task.get("error"),
        )

    # Completed: fetch results from DB
    results = (
        db.query(SimulationResult)
        .filter(SimulationResult.run_id == task_id)
        .order_by(SimulationResult.champion.desc())
        .all()
    )

    bracket_data = (
        db.query(KnockoutBracket)
        .filter(KnockoutBracket.run_id == task_id)
        .order_by(KnockoutBracket.round_name, KnockoutBracket.position)
        .all()
    )

    return TaskProgressResponse(
        status="completed",
        progress=1.0,
        result={
            "standings": [
                {
                    "team_code": r.team_code,
                    "team_name": r.team_name,
                    "round_32": r.round_32,
                    "round_16": r.round_16,
                    "quarter": r.quarter,
                    "semi": r.semi,
                    "final_": r.final_,
                    "champion": r.champion,
                }
                for r in results
            ],
            "bracket": [
                {
                    "round_name": b.round_name,
                    "position": b.position,
                    "team_a": b.team_a_code,
                    "team_b": b.team_b_code,
                    "prob_a": b.prob_a,
                    "prob_b": b.prob_b,
                }
                for b in bracket_data
            ],
        },
    )
