"""Zafronix data query service — reads from local DB cache.

All reads go through this module; the batch_fetch module handles writes.
"""

from datetime import datetime, timedelta

from ..database import SessionLocal
from ..models.zafronix_data import ZafronixMatch, ZafronixStanding, ZafronixTournament


# ── Matches ────────────────────────────────────────────────

def get_matches(
    status: str | None = None,
    stage: str | None = None,
    team_code: str | None = None,
    group_name: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Query cached match results from DB."""
    db = SessionLocal()
    try:
        q = db.query(ZafronixMatch)
        if status:
            q = q.filter(ZafronixMatch.status == status)
        if stage:
            q = q.filter(ZafronixMatch.stage == stage)
        if team_code:
            q = q.filter(
                (ZafronixMatch.team_home_code == team_code) |
                (ZafronixMatch.team_away_code == team_code)
            )
        if group_name:
            q = q.filter(ZafronixMatch.group_name == group_name)

        matches = q.order_by(ZafronixMatch.fetched_at.desc()).limit(limit).all()
        return [_match_to_dict(m) for m in matches]
    finally:
        db.close()


def get_match(match_id: str) -> dict | None:
    """Get single match by ID."""
    db = SessionLocal()
    try:
        m = db.query(ZafronixMatch).filter(ZafronixMatch.match_id == match_id).first()
        return _match_to_dict(m) if m else None
    finally:
        db.close()


def get_match_count() -> dict:
    """Return counts of cached matches by status."""
    db = SessionLocal()
    try:
        total = db.query(ZafronixMatch).count()
        completed = db.query(ZafronixMatch).filter(ZafronixMatch.status == "completed").count()
        latest = db.query(ZafronixMatch.fetched_at).order_by(
            ZafronixMatch.fetched_at.desc()
        ).first()
        return {
            "total": total,
            "completed": completed,
            "latest_fetched": latest[0].isoformat() if latest and latest[0] else None,
        }
    finally:
        db.close()


# ── Standings ─────────────────────────────────────────────

def get_standings(group_name: str | None = None) -> list[dict]:
    """Query cached group standings from DB."""
    db = SessionLocal()
    try:
        q = db.query(ZafronixStanding).filter(
            ZafronixStanding.tournament_year == 2026
        )
        if group_name:
            q = q.filter(ZafronixStanding.group_name == group_name)

        rows = q.order_by(
            ZafronixStanding.group_name,
            ZafronixStanding.position
        ).all()

        return [_standing_to_dict(s) for s in rows]
    finally:
        db.close()


def get_group_standings(group_name: str) -> list[dict]:
    """Get standings for a specific group, sorted by position desc."""
    return get_standings(group_name=group_name)


# ── Tournament ─────────────────────────────────────────────

def get_tournament(year: int = 2026) -> dict | None:
    """Get cached tournament overview."""
    db = SessionLocal()
    try:
        t = db.query(ZafronixTournament).filter(
            ZafronixTournament.tournament_year == year
        ).first()
        if not t:
            return None

        d = {
            "year": t.tournament_year,
            "host_country": t.host_country,
            "champion": t.champion_team_code,
            "runner_up": t.runner_up_code,
            "total_teams": t.total_teams,
            "total_matches": t.total_matches,
            "total_goals": t.total_goals,
            "fetched_at": t.fetched_at.isoformat() if t.fetched_at else None,
        }
        # Include raw_data for bracket/awards/squads access
        if t.raw_data:
            raw_t = t.raw_data.get("tournament", t.raw_data) if isinstance(t.raw_data, dict) else {}
            d["raw"] = t.raw_data
            # Flatten useful nested fields
            if isinstance(raw_t, dict):
                d["edition"] = raw_t.get("edition")
                d["dates"] = raw_t.get("datesIso")
                d["ball_name"] = raw_t.get("ballName")
                d["mascot"] = raw_t.get("mascot")
                d["notes"] = raw_t.get("notes")
                teams_raw = raw_t.get("teams", [])
                if teams_raw and isinstance(teams_raw, list):
                    d["teams_summary"] = [
                        {"name": tm.get("name"), "code": tm.get("code"),
                         "confederation": tm.get("confederation")}
                        for tm in teams_raw if isinstance(tm, dict)
                    ]
        return d
    finally:
        db.close()


# ── Data freshness ─────────────────────────────────────────

def get_cache_status() -> dict:
    """Check freshness of all Zafronix cached data."""
    db = SessionLocal()
    try:
        # Latest fetch times per table
        match_latest = db.query(ZafronixMatch.fetched_at).order_by(
            ZafronixMatch.fetched_at.desc()
        ).first()
        standing_latest = db.query(ZafronixStanding.fetched_at).order_by(
            ZafronixStanding.fetched_at.desc()
        ).first()
        tournament_latest = db.query(ZafronixTournament.fetched_at).order_by(
            ZafronixTournament.fetched_at.desc()
        ).first()

        now = datetime.utcnow()
        def _age(latest):
            if not latest or not latest[0]:
                return None
            delta = now - latest[0]
            hours = delta.total_seconds() / 3600
            return round(hours, 1)

        return {
            "matches": {"count": db.query(ZafronixMatch).count(), "hours_since_update": _age(match_latest)},
            "standings": {"count": db.query(ZafronixStanding).count(), "hours_since_update": _age(standing_latest)},
            "tournament": {"exists": db.query(ZafronixTournament).count() > 0, "hours_since_update": _age(tournament_latest)},
        }
    finally:
        db.close()


# ── Private: serializers ───────────────────────────────────

def _match_to_dict(m: ZafronixMatch) -> dict:
    return {
        "match_id": m.match_id,
        "stage": m.stage,
        "group_name": m.group_name,
        "home": {"code": m.team_home_code, "name": m.team_home_name},
        "away": {"code": m.team_away_code, "name": m.team_away_name},
        "score": {"home": m.score_home, "away": m.score_away},
        "status": m.status,
        "stadium": m.stadium,
        "attendance": m.attendance,
        "referee": m.referee,
        "fetched_at": m.fetched_at.isoformat() if m.fetched_at else None,
    }


def _standing_to_dict(s: ZafronixStanding) -> dict:
    return {
        "group": s.group_name,
        "position": s.position,
        "team": {"code": s.team_code, "name": s.team_name},
        "played": s.played,
        "won": s.won,
        "drawn": s.drawn,
        "lost": s.lost,
        "goals_for": s.goals_for,
        "goals_against": s.goals_against,
        "goal_diff": s.goal_diff,
        "points": s.points,
        "fetched_at": s.fetched_at.isoformat() if s.fetched_at else None,
    }
