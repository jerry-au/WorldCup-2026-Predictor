from fastapi import APIRouter, Depends, HTTPException, Query
from pathlib import Path
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..models.dongqiudi_data import DongqiudiPlayerData
from ..models.player_season_summary import DongqiudiPlayerSeasonSummary
from ..schemas.team import TeamListOut, TeamDetailOut

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "images"


@router.get("")
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

    teams = q.all()
    result = []
    for t in teams:
        flag_url = t.flag_url
        if t.local_flag_path:
            local_path = STATIC_DIR / t.local_flag_path
            if local_path.exists():
                flag_url = f"/static/images/{t.local_flag_path}"
        result.append({
            "code": t.code,
            "name": t.name,
            "name_cn": t.name_cn,
            "iso": t.iso,
            "confederation": t.confederation,
            "group_name": t.group_name,
            "flag_url": flag_url,
            "elo_rating": t.elo_rating,
            "fifa_rank": t.fifa_rank,
        })
    return result


@router.get("/{code}", response_model=TeamDetailOut)
def get_team(code: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.code == code.upper()).first()
    if not team:
        raise HTTPException(404, detail={"code": 1001, "message": "Team not found"})

    # Build player_id -> photo_url + person_name mapping from dongqiudi data
    player_photo_map: dict[int, str] = {}
    player_cn_map: dict[int, str] = {}
    dqd_players = (
        db.query(DongqiudiPlayerData)
        .filter(DongqiudiPlayerData.matched_player_id.isnot(None))
        .all()
    )
    for dpd in dqd_players:
        if dpd.matched_player_id:
            photo_url = dpd.person_logo
            if dpd.local_photo_path:
                # local_photo_path 可能是 "images/xxx.jpg" 或 "player_xxx.jpg"
                filename = dpd.local_photo_path
                if filename.startswith("images/"):
                    filename = filename[len("images/"):]
                local_path = STATIC_DIR / filename
                if local_path.exists():
                    photo_url = f"/static/images/{filename}"
            player_photo_map[dpd.matched_player_id] = photo_url
            if dpd.person_name:
                player_cn_map[dpd.matched_player_id] = dpd.person_name

    # Resolve team flag URL
    flag_url = team.flag_url
    if team.local_flag_path:
        local_flag = STATIC_DIR / team.local_flag_path
        if local_flag.exists():
            flag_url = f"/static/images/{team.local_flag_path}"

    # 批量加载所有球员的赛季统计（避免 N+1 查询）
    player_ids = [p.id for p in team.players]
    all_stats = (
        db.query(DongqiudiPlayerSeasonSummary)
        .filter(DongqiudiPlayerSeasonSummary.matched_player_id.in_(player_ids))
        .all()
    )
    stats_by_player: dict[int, list] = {}
    for s in all_stats:
        stats_by_player.setdefault(s.matched_player_id, []).append(s)

    players_out = []
    for p in team.players:
        dqd_stats = stats_by_player.get(p.id, [])
        stats_out = [
            {
                "category": s.category,
                "season": s.season,
                "club_name": s.club_name,
                "competition_name": s.competition_name,
                "appearances": s.appearances,
                "starts": s.starts,
                "goals": s.goals,
                "assists": s.assists,
                "yellow_cards": s.yellow_cards,
                "red_cards": s.red_cards,
            }
            for s in dqd_stats
        ]
        best_pos = p.position
        players_out.append({
            "name": p.name,
            "name_cn": player_cn_map.get(p.id),
            "jersey": p.jersey,
            "position": p.position,
            "club_name": p.club_name,
            "age_at_tournament": p.age_at_tournament,
            "season_stats": stats_out,
            "best_position": best_pos,
            "photo_url": player_photo_map.get(p.id),
        })

    starting_xi = _compute_starting_xi(players_out)

    return {
        "code": team.code,
        "name": team.name,
        "name_cn": team.name_cn,
        "iso": team.iso,
        "confederation": team.confederation,
        "group_name": team.group_name,
        "flag_url": flag_url,
        "elo_rating": team.elo_rating,
        "fifa_rank": team.fifa_rank,
        "market_value_eur": team.market_value_eur,
        "coach_name": team.coach_name,
        "coach_country": team.coach_country,
        "players": players_out,
        "starting_xi": starting_xi,
    }


def _compute_starting_xi(players: list[dict]) -> list[dict]:
    """Select starting XI in 4-3-3 formation based on starts (首发次数).
    If no season stats available, just take first 11 players by position.
    """
    formation = {"GK": 1, "DF": 4, "MF": 3, "FW": 3}
    selected = []
    for pos, count in formation.items():
        candidates = [p for p in players if p.get("position") == pos and p not in selected]
        if not candidates:
            continue
        # Sort by total starts (more = better), if no starts then keep original order
        candidates.sort(
            key=lambda p: sum(s.get("starts", 0) for s in p.get("season_stats", [])),
            reverse=True,
        )
        selected.extend(candidates[:count])
    # Always return a list (can be empty), never None
    return selected
