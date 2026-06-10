from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..models.player_stats import PlayerSeasonStats
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

    players_out = []
    for p in team.players:
        stats = (
            db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.player_id == p.id)
            .all()
        )
        stats_out = [
            {
                "competition_code": s.competition_code,
                "competition_name": s.competition_name,
                "goals": s.goals,
                "assists": s.assists,
                "appearances": s.appearances,
                "minutes_played": s.minutes_played,
            }
            for s in stats
        ]
        best_pos = p.position
        players_out.append({
            "name": p.name,
            "jersey": p.jersey,
            "position": p.position,
            "club_name": p.club_name,
            "age_at_tournament": p.age_at_tournament,
            "season_stats": stats_out,
            "best_position": best_pos,
        })

    starting_xi = _compute_starting_xi(players_out)

    return {
        "code": team.code,
        "name": team.name,
        "iso": team.iso,
        "confederation": team.confederation,
        "group_name": team.group_name,
        "flag_url": team.flag_url,
        "elo_rating": team.elo_rating,
        "fifa_rank": team.fifa_rank,
        "market_value_eur": team.market_value_eur,
        "coach_name": team.coach_name,
        "coach_country": team.coach_country,
        "players": players_out,
        "starting_xi": starting_xi,
    }


def _compute_starting_xi(players: list[dict]) -> list[dict] | None:
    """Select starting XI in 4-3-3 formation based on minutes played."""
    formation = {"GK": 1, "DF": 4, "MF": 3, "FW": 3}
    selected = []

    for pos, count in formation.items():
        candidates = [p for p in players if p.get("position") == pos and p not in selected]
        candidates.sort(
            key=lambda p: sum(s["minutes_played"] for s in p.get("season_stats", [])),
            reverse=True,
        )
        selected.extend(candidates[:count])

    return selected if selected else None
