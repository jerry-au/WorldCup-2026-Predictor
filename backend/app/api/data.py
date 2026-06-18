"""Data management API — trigger and monitor batch fetching, data refresh status."""

import asyncio
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks

from ..database import get_db, SessionLocal
from ..services.fetcher import DataFetcher
from ..tasks.scheduler import (
    get_data_source_status,
    get_recent_refresh_logs,
    is_matchday,
    get_refresh_mode,
    get_refresh_interval_hours,
    refresh_elo_rankings,
)
from ..models.data_refresh_log import DataRefreshLog

router = APIRouter(prefix="/api/v1/data", tags=["data"])

# Thread pool for blocking scrape operations
_executor = ThreadPoolExecutor(max_workers=4)

# In-memory task tracking (resets on server restart)
_active_tasks: dict[str, dict] = {}


def _run_async_task(task_id: str, source: str, refresh_type: str, func, *args, **kwargs):
    """Run a blocking scrape function in thread pool with progress tracking."""
    _active_tasks[task_id] = {
        "status": "running",
        "progress": 0.0,
        "source": source,
        "refresh_type": refresh_type,
        "started_at": datetime.utcnow().isoformat(),
    }
    db = SessionLocal()
    log = DataRefreshLog.log_start(source, refresh_type)
    db.add(log)
    db.commit()

    try:
        result = func(*args, **kwargs)
        log.mark_complete(
            records_updated=result.get("records_saved", 0) if isinstance(result, dict) else 0,
            details=str(result)[:2000] if result else None,
        )
        _active_tasks[task_id] = {
            "status": "success",
            "progress": 100.0,
            "source": source,
            "refresh_type": refresh_type,
            "result": result if isinstance(result, dict) else {"status": "ok"},
        }
    except Exception as e:
        log.mark_failed(str(e))
        _active_tasks[task_id] = {
            "status": "failed",
            "progress": _active_tasks.get(task_id, {}).get("progress", 0),
            "source": source,
            "refresh_type": refresh_type,
            "error": str(e),
        }
    finally:
        db.commit()
        db.close()


@router.get("/refresh/progress/{task_id}")
def get_task_progress(task_id: str):
    """Get progress of an active or completed task."""
    task = _active_tasks.get(task_id)
    if not task:
        # Check DB for recently completed tasks
        db = next(get_db())
        recent_log = (
            db.query(DataRefreshLog)
            .filter(DataRefreshLog.status.in_(["running", "success", "failed"]))
            .order_by(DataRefreshLog.started_at.desc())
            .first()
        )
        db.close()
        if recent_log:
            return {
                "task_id": task_id,
                "status": recent_log.status,
                "progress": recent_log.progress or (100.0 if recent_log.status == "success" else 0.0),
                "source": recent_log.source,
                "refresh_type": recent_log.refresh_type,
                "records_updated": recent_log.records_updated,
                "error_message": recent_log.error_message,
            }
        return {"task_id": task_id, "status": "not_found", "progress": 0}
    return {"task_id": task_id, **task}


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
def trigger_dongqiudi_national_rosters(background_tasks: BackgroundTasks):
    """Scrape World Cup national-team rosters from Dongqiudi (async)."""
    from ..tasks.dongqiudi_fetch import run_dongqiudi_national_rosters

    task_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(
        _run_async_task, task_id, "dongqiudi", "national_rosters",
        run_dongqiudi_national_rosters
    )
    return {"status": "accepted", "task_id": task_id, "message": "任务已提交，正在后台执行"}


@router.post("/fetch/dongqiudi/player-season-summaries")
def trigger_player_season_summaries(background_tasks: BackgroundTasks):
    """Scrape player season summary data from Dongqiudi (async)."""
    from ..services.dongqiudi_player_season_summaries import scrape_all_player_season_summaries

    task_id = str(uuid.uuid4())[:8]

    def _run():
        db = SessionLocal()
        try:
            result = scrape_all_player_season_summaries(db)
            return result
        finally:
            db.close()

    background_tasks.add_task(
        _run_async_task, task_id, "dongqiudi", "player_season_summaries", _run
    )
    return {"status": "accepted", "task_id": task_id, "message": "任务已提交，正在后台执行"}


@router.post("/fetch/dongqiudi/player-abilities")
def trigger_player_abilities(background_tasks: BackgroundTasks):
    """Scrape player ability data from Dongqiudi (async)."""
    from ..services.dongqiudi_player_ability import scrape_all_player_abilities

    task_id = str(uuid.uuid4())[:8]

    def _run():
        db = SessionLocal()
        try:
            result = scrape_all_player_abilities(db)
            return result
        finally:
            db.close()

    background_tasks.add_task(
        _run_async_task, task_id, "dongqiudi", "player_abilities", _run
    )
    return {"status": "accepted", "task_id": task_id, "message": "任务已提交，正在后台执行"}


@router.post("/fetch/standings")
def trigger_fetch_standings(background_tasks: BackgroundTasks):
    """Fetch group standings from Dongqiudi (async)."""
    from ..services.dongqiudi_standings import scrape_all_standings

    task_id = str(uuid.uuid4())[:8]

    def _run():
        db = SessionLocal()
        try:
            result = scrape_all_standings(db)
            return result
        finally:
            db.close()

    background_tasks.add_task(
        _run_async_task, task_id, "dongqiudi", "standings", _run
    )
    return {"status": "accepted", "task_id": task_id, "message": "任务已提交，正在后台执行"}


@router.post("/fetch/results")
def trigger_fetch_results(background_tasks: BackgroundTasks):
    """Fetch match schedule and results from Dongqiudi (async)."""
    from ..services.dongqiudi_match_results import scrape_all_matches

    task_id = str(uuid.uuid4())[:8]

    def _run():
        db = SessionLocal()
        try:
            result = scrape_all_matches(db)
            return result
        finally:
            db.close()

    background_tasks.add_task(
        _run_async_task, task_id, "dongqiudi", "match_results", _run
    )
    return {"status": "accepted", "task_id": task_id, "message": "任务已提交，正在后台执行"}


@router.post("/fetch/elo-rankings")
def trigger_elo_rankings():
    """Fetch Elo ratings from eloratings.net and update team elo_rating + fifa_rank."""
    from ..database import SessionLocal
    from ..services.elo_rankings_fetcher import fetch_and_update_elo

    db = next(get_db())
    try:
        result = fetch_and_update_elo(db)
        return {"status": "ok", **result}
    finally:
        db.close()


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

    # Count matches and standings from dongqiudi tables
    from ..models.dongqiudi_match import DongqiudiMatch
    from ..models.odds_data import MatchOddsSummary

    db2 = next(get_db())
    dqd_matches = db2.query(DongqiudiMatch).count()
    dqd_standings = 0
    completed_matches = db2.query(DongqiudiMatch).filter(
        DongqiudiMatch.status == "completed"
    ).count()
    # standings table may not exist yet
    try:
        from ..models.dongqiudi_standing import DongqiudiStanding
        dqd_standings = db2.query(DongqiudiStanding).count()
    except Exception:
        pass
    odds_count = db2.query(MatchOddsSummary).count()
    db2.close()

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
        "dongqiudi_matches": dqd_matches,
        "dongqiudi_completed_matches": completed_matches,
        "dongqiudi_standings": dqd_standings,
        "queue": {
            **fetcher.queue_status(),
            "odds": odds_count,
        },
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
        refresh_dongqiudi_matches,
    )

    triggers = {
        "recommendations": precompute_recommendations,
        "odds": refresh_odds_data,
        "player_data": refresh_player_data,
        "dongqiudi": refresh_dongqiudi_rosters,
        "match_results": refresh_dongqiudi_matches,
        "elo": refresh_elo_rankings,
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
