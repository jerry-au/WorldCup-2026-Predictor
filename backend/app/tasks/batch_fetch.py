"""Batch data fetching orchestration.

Run via API trigger or scheduled interval.
Usage:
    from app.tasks.batch_fetch import run_football_data_batch
    result = run_football_data_batch()
"""

from datetime import datetime

from ..database import SessionLocal
from ..services.fetcher import DataFetcher, FetchJob
from ..models.zafronix_data import ZafronixMatch, ZafronixStanding, ZafronixTournament
from ..models.team import Team

# -- football-data.org --

def run_football_data_batch() -> dict:
    """Fetch scorers from all target leagues via football-data.org.

    Respects 10 req/min rate limit. Processes ~10 leagues = ~10 req.
    """
    from ..services.football_data_fetcher import enqueue_scorers

    db = SessionLocal()
    fetcher = DataFetcher()

    try:
        jobs = enqueue_scorers(fetcher, db)
        results = fetcher.run_batch(batch_size=jobs)
    finally:
        db.close()

    success = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")

    return {
        "source": "football-data.org",
        "total_jobs": len(results),
        "success": success,
        "failed": failed,
        "queue_remaining": fetcher.queue_status()["queue_length"],
    }


# -- Zafronix --

ZAFRONIX_BASE = "https://api.zafronix.com/fifa/worldcup/v1"

ZAFRONIX_ENDPOINTS = [
    ("matches", {"tournament": "2026", "status": "completed"}, "match_results"),
    ("standings", {"tournament": "2026"}, "group_standings"),
    ("tournaments/2026", {}, "full_tournament"),
]


def run_zafronix_batch() -> dict:
    """Fetch matches + standings + full tournament from Zafronix -> save to DB.

    3 API calls total per day. Free tier: 1,000/day.
    All data persisted locally; reads go to DB, not API.
    """
    from ..config import settings

    if not settings.zafronix_api_key:
        return {"source": "zafronix", "total_jobs": 0, "success": 0, "failed": 0,
                "skipped_reason": "no_api_key"}

    fetcher = DataFetcher()
    for endpoint, params, _label in ZAFRONIX_ENDPOINTS:
        job = FetchJob(
            source="zafronix",
            url=f"{ZAFRONIX_BASE}/{endpoint}",
            params=params,
            headers={"X-API-Key": settings.zafronix_api_key},
            priority=10,
        )
        fetcher.enqueue(job)

    results = fetcher.run_batch(batch_size=len(ZAFRONIX_ENDPOINTS))

    # Save each endpoint's data to DB
    db = SessionLocal()
    now = datetime.utcnow()
    saved_stats = {"matches": 0, "standings": 0, "tournament": 0}

    try:
        teams_by_name = {t.name.lower(): t.code for t in db.query(Team).all()}

        for i, result in enumerate(results):
            label = ZAFRONIX_ENDPOINTS[i][2]
            if result["status"] != "ok":
                continue
            data = result.get("data")

            if label == "match_results":
                saved_stats["matches"] = _save_matches(db, data, now, teams_by_name)
            elif label == "group_standings":
                saved_stats["standings"] = _save_standings(db, data, now, teams_by_name)
            elif label == "full_tournament":
                saved_stats["tournament"] = _save_tournament(db, data, now)

        db.commit()
    except Exception as e:
        db.rollback()
        saved_stats["_error"] = str(e)
    finally:
        db.close()

    success = sum(1 for r in results if r["status"] == "ok")
    failed = sum(1 for r in results if r["status"] == "error")

    return {
        "source": "zafronix",
        "endpoints_fetched": [e[2] for e in ZAFRONIX_ENDPOINTS],
        "saved_to_db": saved_stats,
        "total_api_calls": len(results),
        "success": success,
        "failed": failed,
    }


def _save_matches(db, matches_data, now, teams_by_name) -> int:
    """Parse matches list and upsert into zafronix_matches."""
    if not isinstance(matches_data, list):
        matches_data = [matches_data] if isinstance(matches_data, dict) else []

    count = 0
    for m in matches_data:
        if not isinstance(m, dict):
            continue

        match_id = m.get("id") or f"{m.get('home_team','')}_{m.get('away_team','')}"
        home_name = m.get("home_team", "")
        away_name = m.get("away_team", "")

        home_code = teams_by_name.get(home_name.lower())
        away_code = teams_by_name.get(away_name.lower())

        score = m.get("score", {})
        existing = db.query(ZafronixMatch).filter(
            ZafronixMatch.match_id == match_id
        ).first()

        row = {
            "match_id": match_id,
            "stage": m.get("stage") or m.get("round"),
            "group_name": m.get("group") or m.get("group_name"),
            "team_home_code": home_code,
            "team_away_code": away_code,
            "team_home_name": home_name,
            "team_away_name": away_name,
            "score_home": score.get("home") if isinstance(score, dict) else None,
            "score_away": score.get("away") if isinstance(score, dict) else None,
            "status": m.get("status", "completed"),
            "stadium": m.get("stadium") or (m.get("venue", {}).get("name") if isinstance(m.get("venue"), dict) else None),
            "attendance": m.get("attendance"),
            "referee": m.get("referee"),
            "raw_data": m,
            "fetched_at": now,
        }

        if existing:
            for k, v in row.items():
                if k != "match_id":
                    setattr(existing, k, v)
        else:
            db.add(ZafronixMatch(**row))
        count += 1

    return count


def _save_standings(db, standings_data, now, teams_by_name) -> int:
    """Parse standings and upsert into zafronix_standings."""
    groups = standings_data.get("groups", []) if isinstance(standings_data, dict) else []
    if not groups and isinstance(standings_data, list):
        groups = standings_data

    count = 0
    for group in groups:
        if not isinstance(group, dict):
            continue
        group_name = group.get("group") or group.get("name") or group.get("letter")
        entries = group.get("teams") or group.get("table") or group.get("standings") or []
        if not entries and "entries" in group:
            entries = group["entries"]

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            team_name = entry.get("team") or entry.get("team_name") or ""
            team_code = teams_by_name.get(team_name.lower())

            existing = db.query(ZafronixStanding).filter(
                ZafronixStanding.tournament_year == 2026,
                ZafronixStanding.group_name == group_name,
                ZafronixStanding.team_code == team_code,
            ).first()

            row = {
                "tournament_year": 2026,
                "group_name": group_name,
                "position": entry.get("position") or entry.get("rank"),
                "team_code": team_code,
                "team_name": team_name,
                "played": entry.get("played") or entry.get("matches_played"),
                "won": entry.get("won") or entry.get("wins"),
                "drawn": entry.get("drawn") or entry.get("draws"),
                "lost": entry.get("lost") or entry.get("losses"),
                "goals_for": entry.get("goals_for") or entry.get("gf"),
                "goals_against": entry.get("goals_against") or entry.get("ga"),
                "goal_diff": entry.get("goal_diff") or entry.get("gd"),
                "points": entry.get("points") or entry.get("pts"),
                "raw_data": entry,
                "fetched_at": now,
            }

            if existing:
                for k, v in row.items():
                    if k != "tournament_year" and k != "group_name" and k != "team_code":
                        setattr(existing, k, v)
            else:
                db.add(ZafronixStanding(**row))
            count += 1

    return count


def _save_tournament(db, tournament_data, now) -> int:
    """Save tournament overview to zafronix_tournament."""
    if not isinstance(tournament_data, dict):
        return 0

    # Zafronix wraps data in a "tournament" key
    t = tournament_data.get("tournament", tournament_data)
    if not isinstance(t, dict):
        return 0

    champion = t.get("champion") or {}
    runner_up = t.get("runnerUp") or {}

    existing = db.query(ZafronixTournament).filter(
        ZafronixTournament.tournament_year == 2026
    ).first()

    row = {
        "tournament_year": 2026,
        "host_country": ", ".join(t.get("host", [])) if isinstance(t.get("host"), list) else t.get("host"),
        "champion_team_code": champion.get("code") if isinstance(champion, dict) else None,
        "runner_up_code": runner_up.get("code") if isinstance(runner_up, dict) else None,
        "total_teams": t.get("teamsCount"),
        "total_matches": t.get("matchesCount"),
        "total_goals": t.get("totalGoals"),
        "raw_data": tournament_data,   # store full response for bracket/awards access
        "fetched_at": now,
    }

    if existing:
        for k, v in row.items():
            if k != "tournament_year":
                setattr(existing, k, v)
    else:
        db.add(ZafronixTournament(**row))

    return 1
