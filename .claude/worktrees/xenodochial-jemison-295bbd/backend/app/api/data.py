"""Data management API — trigger and monitor batch fetching."""

from fastapi import APIRouter

from ..database import get_db
from ..services.fetcher import DataFetcher

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
    """Fetch latest match results from Zafronix."""
    from ..tasks.batch_fetch import run_zafronix_results_batch

    result = run_zafronix_results_batch()
    return {"status": "ok", "result": result}


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
