from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..schemas.team import TeamListOut, TeamDetailOut

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.get("", response_model=list[TeamListOut])
def list_teams(
    confederation: str | None = Query(None),
    group: str | None = Query(None),
    sort_by: str = Query("elo_rating", pattern="^(elo_rating|fifa_rank|name)$"),
    db: Session = Depends(get_db),
):
    q = db.query(Team)
    if confederation:
        q = q.filter(Team.confederation.ilike(f"%{confederation}%"))
    if group:
        q = q.filter(Team.group_name == group.upper())

    col = getattr(Team, sort_by, Team.elo_rating)
    q = q.order_by(col.desc() if sort_by != "name" else col.asc())

    return q.all()


@router.get("/{code}", response_model=TeamDetailOut)
def get_team(code: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.code == code.upper()).first()
    if not team:
        raise HTTPException(404, detail={"code": 1001, "message": "Team not found"})
    return team
