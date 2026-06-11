"""Data management API — trigger and monitor batch fetching, data refresh status."""

from datetime import datetime

from fastapi import APIRouter

from ..database import get_db
from ..services.fetcher import DataFetcher
from ..tasks.scheduler import (
    get_data_source_status,
    get_recent_refresh_logs,
    is_matchday,
    get_refresh_mode,
    get_refresh_interval_hours,
)

router = APIRouter(prefix="/api/v1/data", tags=["data"])


@router.post("/fetch/scorers")
def trigger_fetch_scorers():
    """Fetch top scorer data from football-data.org for all target leagues."""
    from ..tasks.batch_fetch import run_football_data_batch

    result = run_football_data_batch()
    return {"status": "ok", "result": result}


@router.post("/fetch/dongqiudi")
def trigger_dongqiudi():
    """Scrape player stats from dongqiudi for all supported leagues."""
    from ..tasks.dongqiudi_fetch import run_dongqiudi_scrape

    result = run_dongqiudi_scrape()
    return {"status": "ok", "result": result}


@router.post("/fetch/dongqiudi/national-rosters")
def trigger_dongqiudi_national_rosters():
    """Scrape World Cup national-team rosters from Dongqiudi."""
    from ..tasks.dongqiudi_fetch import run_dongqiudi_national_rosters

    result = run_dongqiudi_national_rosters()
    return {"status": "ok", "result": result}


@router.post("/fetch/results")
def trigger_fetch_results():
    """Fetch matches + standings + tournament from Zafronix → save to local DB."""
    from ..tasks.batch_fetch import run_zafronix_batch

    result = run_zafronix_batch()
    return {"status": "ok", "result": result}


# ── Zafronix read endpoints (from DB) ────────────────────────

@router.get("/zafronix/matches")
def list_zafronix_matches(
    status: str | None = None,
    stage: str | None = None,
    team_code: str | None = None,
    group_name: str | None = None,
):
    """Read cached match results from local DB (no API call)."""
    from ..services.zafronix_service import get_matches, get_match_count

    matches = get_matches(status=status, stage=stage, team_code=team_code, group_name=group_name)
    count_info = get_match_count()
    return {"matches": matches, "total": len(matches), "cache": count_info}


@router.get("/zafronix/standings")
def list_zafronix_standings(group_name: str | None = None):
    """Read cached group standings from local DB (no API call)."""
    from ..services.zafronix_service import get_standings

    standings = get_standings(group_name=group_name)
    return {"standings": standings, "total": len(standings)}


@router.get("/zafronix/tournament")
def get_zafronix_tournament():
    """Read cached tournament overview from local DB (no API call)."""
    from ..services.zafronix_service import get_tournament

    t = get_tournament(2026)
    if not t:
        return {"error": "No tournament data cached. Run POST /fetch/results first."}
    return t


@router.get("/zafronix/cache-status")
def zafronix_cache_status():
    """Check freshness of Zafronix data in local DB."""
    from ..services.zafronix_service import get_cache_status
    return get_cache_status()


@router.get("/fetch/status")
def fetch_status():
    """Check the fetch queue status and data coverage summary."""
    from ..models.player_stats import PlayerSeasonStats
    from ..models.player import Player
    from ..models.dongqiudi_data import (
        DongqiudiTeamData,
        DongqiudiCoachData,
        DongqiudiPlayerData,
    )

    db = next(get_db())
    total_stats = db.query(PlayerSeasonStats).count()
    total_players = db.query(Player).count()
    by_source = {}
    for s in db.query(PlayerSeasonStats.source,
                       PlayerSeasonStats.competition_code).all():
        src = s.source or "?"
        by_source[src] = by_source.get(src, 0) + 1

    dqd_teams = db.query(DongqiudiTeamData).count()
    dqd_coaches = db.query(DongqiudiCoachData).count()
    dqd_players = db.query(DongqiudiPlayerData).count()
    dqd_matched = db.query(DongqiudiPlayerData).filter(
        DongqiudiPlayerData.matched_player_id.isnot(None)
    ).count()
    db.close()

    fetcher = DataFetcher()
    return {
        "player_stats_imported": total_stats,
        "players_total": total_players,
        "coverage_pct": round(total_stats / total_players * 100, 1) if total_players else 0,
        "by_source": by_source,
        "dongqiudi_national_rosters": {
            "teams": dqd_teams,
            "coaches": dqd_coaches,
            "players": dqd_players,
            "matched_players": dqd_matched,
            "match_coverage_pct": round(dqd_matched / dqd_players * 100, 1) if dqd_players else 0,
        },
        "queue": fetcher.queue_status(),
    }


@router.get("/refresh/status")
def refresh_status():
    """Get current data refresh status and scheduler information."""
    sources = get_data_source_status()
    recent_logs = get_recent_refresh_logs(limit=5)
    match_day = is_matchday()
    refresh_mode = get_refresh_mode()
    interval_hours = get_refresh_interval_hours()

    return {
        "scheduler": {
            "match_day": match_day,
            "refresh_mode": refresh_mode.value,
            "refresh_interval_hours": interval_hours,
            "is_match_day_mode": refresh_mode.value == "match_day",
        },
        "sources": sources,
        "recent_logs": recent_logs,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/refresh/trigger")
def trigger_refresh(source: str = "all"):
    """Manually trigger a data refresh for specified source or all sources."""
    from ..tasks.scheduler import (
        precompute_recommendations,
        refresh_odds_data,
        refresh_player_data,
        refresh_dongqiudi_rosters,
        refresh_zafronix_results,
    )

    triggers = {
        "recommendations": precompute_recommendations,
        "odds": refresh_odds_data,
        "player_data": refresh_player_data,
        "dongqiudi": refresh_dongqiudi_rosters,
        "zafronix": refresh_zafronix_results,
    }

    if source == "all":
        results = {}
        for name, func in triggers.items():
            try:
                if hasattr(func, '__await__'):
                    import asyncio
                    asyncio.run(func())
                results[name] = {"status": "triggered"}
            except Exception as e:
                results[name] = {"status": "error", "message": str(e)}
        return {"status": "ok", "results": results}

    if source not in triggers:
        return {"status": "error", "message": f"Unknown source: {source}"}

    try:
        func = triggers[source]
        if hasattr(func, '__await__'):
            import asyncio
            asyncio.run(func())
        return {"status": "ok", "source": source, "message": "Refresh triggered"}
    except Exception as e:
        return {"status": "error", "source": source, "message": str(e)}


@router.get("/refresh/logs")
def refresh_logs(limit: int = 20):
    """Get recent data refresh operation logs."""
    logs = get_recent_refresh_logs(limit=min(limit, 100))
    return {"logs": logs, "count": len(logs)}
