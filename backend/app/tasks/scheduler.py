"""Data sync scheduler with dynamic refresh strategy based on match day status."""

from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import json

from ..database import SessionLocal
from ..models.team import Team
from ..models.recommendation_cache import RecommendationCache
from ..models.odds_data import MatchOdds, MatchOddsSummary
from ..models.data_refresh_log import DataRefreshLog, DataSourceStatus
from ..core.prediction import PredictionEngine
from ..services.recommendation import recommendation_engine
from ..services.odds import odds_client
from ..services.football_data_fetcher import football_data_fetcher


class MatchBucket(Enum):
    TODAY = "today"
    SOON = "soon"
    LATER = "later"
    NOT_MATCHDAY = "off"


class RefreshMode(Enum):
    MATCH_DAY = "match_day"
    NORMAL = "normal"


def get_match_bucket(match_date: date, today: Optional[date] = None) -> MatchBucket:
    if today is None:
        today = date.today()
    days_until = (match_date - today).days
    if days_until < 0:
        return MatchBucket.LATER
    elif days_until == 0:
        return MatchBucket.TODAY
    elif days_until <= 2:
        return MatchBucket.SOON
    else:
        return MatchBucket.LATER


def is_matchday(today: Optional[date] = None) -> bool:
    if today is None:
        today = date.today()
    start = date(2026, 6, 11)
    end = date(2026, 7, 19)
    return start <= today <= end


def get_refresh_mode() -> RefreshMode:
    return RefreshMode.MATCH_DAY if is_matchday() else RefreshMode.NORMAL


def get_refresh_interval_hours() -> int:
    return 4 if get_refresh_mode() == RefreshMode.MATCH_DAY else 8


def needs_odds_refresh(
    last_refresh: Optional[datetime],
    match_date: date,
    today: Optional[date] = None,
) -> bool:
    bucket = get_match_bucket(match_date, today)
    now = datetime.now()

    if bucket == MatchBucket.TODAY:
        interval = 4 if get_refresh_mode() == RefreshMode.MATCH_DAY else 8
        if last_refresh is None:
            return True
        hours_since = (now - last_refresh).total_seconds() / 3600
        return hours_since >= interval

    elif bucket == MatchBucket.SOON:
        if last_refresh is None:
            return True
        today_date = today or date.today()
        return last_refresh.date() < today_date

    else:
        return False


def needs_result_refresh(
    last_refresh: Optional[datetime],
    is_live: bool,
) -> bool:
    if not is_live:
        return False
    if last_refresh is None:
        return True
    minutes_since = (datetime.now() - last_refresh).total_seconds() / 60
    return minutes_since >= 15


def needs_standings_refresh(
    last_refresh: Optional[datetime],
    match_just_finished: bool,
) -> bool:
    if match_just_finished:
        return True
    return False


def _upsert_cache(db, cache_type, team_a_code, team_b_code, result_data, computed_at, expires_at):
    existing = db.query(RecommendationCache).filter(
        RecommendationCache.cache_type == cache_type,
        RecommendationCache.team_a_code == team_a_code,
        RecommendationCache.team_b_code == team_b_code,
    ).first()

    if existing:
        existing.result_data = result_data
        existing.computed_at = computed_at
        existing.expires_at = expires_at
    else:
        db.add(RecommendationCache(
            cache_type=cache_type,
            team_a_code=team_a_code,
            team_b_code=team_b_code,
            result_data=result_data,
            computed_at=computed_at,
            expires_at=expires_at,
        ))


async def precompute_recommendations():
    """Precompute value bets and discrepancies for all same-group matchups."""
    db = SessionLocal()
    log = DataRefreshLog.log_start("internal", "precompute_recommendations")
    db.add(log)
    db.commit()

    try:
        engine = PredictionEngine()
        teams = db.query(Team).all()
        ttl = RecommendationCache.default_ttl()
        refresh_mode = get_refresh_mode()
        ttl = timedelta(hours=4) if refresh_mode == RefreshMode.MATCH_DAY else timedelta(hours=8)

        scanned = 0
        for i, team_a in enumerate(teams):
            for j, team_b in enumerate(teams):
                if j <= i or team_a.group_name != team_b.group_name:
                    continue
                if scanned >= 12:
                    break

                pred = engine.predict(team_a, team_b, db=db, match_type="group")
                odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)

                betting = recommendation_engine.analyze(
                    system_probs=pred["probabilities"],
                    system_confidence=pred["system_confidence"],
                    odds_data=odds_data,
                )

                now = datetime.utcnow()

                _upsert_cache(
                    db, "value_bets", team_a.code, team_b.code,
                    json.dumps(betting["recommendations"], ensure_ascii=False),
                    now, now + ttl,
                )

                _upsert_cache(
                    db, "discrepancies", team_a.code, team_b.code,
                    json.dumps(betting["discrepancy"], ensure_ascii=False),
                    now, now + ttl,
                )

                scanned += 1
            if scanned >= 12:
                break

        db.commit()
        log.mark_complete(records_updated=scanned, details=f"mode={refresh_mode.value}")
    except Exception as e:
        log.mark_failed(str(e))
        db.commit()
    finally:
        db.close()


async def refresh_odds_data():
    """Fetch BetExplorer odds and save matching teams to DB."""
    db = SessionLocal()
    log = DataRefreshLog.log_start("betexplorer", "odds_refresh")
    db.add(log)
    db.commit()

    try:
        result = await odds_client.fetch_all_and_cache()
        if result.get("status") == "ok":
            log.mark_complete(records_updated=result.get("pairs_saved", 0))
        else:
            log.mark_failed(result.get("reason", "unknown"))
        db.commit()
    except Exception as e:
        log.mark_failed(str(e))
        db.commit()
    finally:
        db.close()


async def refresh_player_data():
    """Refresh player data from Football-Data.org."""
    db = SessionLocal()
    log = DataRefreshLog.log_start("football-data-org", "player_stats")
    db.add(log)
    db.commit()

    try:
        await football_data_fetcher.refresh_player_data()
        log.mark_complete()
        db.commit()
    except Exception as e:
        log.mark_failed(str(e))
        db.commit()
    finally:
        db.close()


async def refresh_dongqiudi_rosters():
    """Refresh national team rosters from Dongqiudi."""
    from ..services.dongqiudi_national_roster import scrape_all_national_rosters

    db = SessionLocal()
    log = DataRefreshLog.log_start("dongqiudi", "national_rosters")
    db.add(log)
    db.commit()

    try:
        result = scrape_all_national_rosters(db)
        log.mark_complete(
            records_updated=result.get("players_saved", 0),
            details=json.dumps(result, ensure_ascii=False),
        )
        db.commit()
    except Exception as e:
        log.mark_failed(str(e))
        db.commit()
    finally:
        db.close()


async def refresh_elo_rankings():
    """Fetch Elo ratings from eloratings.net and update team elo_rating + fifa_rank."""
    from ..services.elo_rankings_fetcher import fetch_and_update_elo

    db = SessionLocal()
    log = DataRefreshLog.log_start("eloratings", "elo_rankings")
    db.add(log)
    db.commit()

    try:
        result = fetch_and_update_elo(db)
        log.mark_complete(
            records_updated=result.get("teams_updated", 0),
            details=json.dumps(result, ensure_ascii=False),
        )
        db.commit()
    except Exception as e:
        log.mark_failed(str(e))
        db.commit()
    finally:
        db.close()


async def refresh_zafronix_results():
    """Fetch matches + standings + full tournament from Zafronix (daily at noon)."""
    from ..tasks.batch_fetch import run_zafronix_batch

    db = SessionLocal()
    log = DataRefreshLog.log_start("zafronix", "full_sync")
    db.add(log)
    db.commit()

    try:
        result = run_zafronix_batch()
        log.mark_complete(
            records_updated=result.get("success", 0),
            details=json.dumps(result, ensure_ascii=False),
        )
        db.commit()
    except Exception as e:
        log.mark_failed(str(e))
        db.commit()
    finally:
        db.close()


def get_data_source_status() -> list[dict]:
    """Get current status of all data sources."""
    db = SessionLocal()
    try:
        sources = db.query(DataSourceStatus).all()
        return [
            {
                "source": s.source,
                "last_refresh": s.last_refresh.isoformat() if s.last_refresh else None,
                "next_scheduled": s.next_scheduled.isoformat() if s.next_scheduled else None,
                "is_active": bool(s.is_active),
                "refresh_interval_hours": s.refresh_interval_hours,
                "match_day_interval_hours": s.match_day_interval_hours,
                "needs_refresh": s.needs_refresh(is_matchday()),
            }
            for s in sources
        ]
    finally:
        db.close()


def get_recent_refresh_logs(limit: int = 10) -> list[dict]:
    """Get recent refresh operation logs."""
    db = SessionLocal()
    try:
        logs = db.query(DataRefreshLog).order_by(
            DataRefreshLog.started_at.desc()
        ).limit(limit).all()
        return [
            {
                "id": log.id,
                "source": log.source,
                "refresh_type": log.refresh_type,
                "status": log.status,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                "records_updated": log.records_updated,
                "error_message": log.error_message,
            }
            for log in logs
        ]
    finally:
        db.close()


def init_data_source_status():
    """Initialize data source status records."""
    db = SessionLocal()
    try:
        default_sources = [
            {"source": "betexplorer", "refresh_interval_hours": 8, "match_day_interval_hours": 4},
            {"source": "football-data-org", "refresh_interval_hours": 12, "match_day_interval_hours": 12},
            {"source": "dongqiudi", "refresh_interval_hours": 24, "match_day_interval_hours": 12},
            {"source": "zafronix", "refresh_interval_hours": 24, "match_day_interval_hours": 24},
            {"source": "eloratings", "refresh_interval_hours": 24, "match_day_interval_hours": 12},
            {"source": "internal", "refresh_interval_hours": 8, "match_day_interval_hours": 4},
        ]

        for src in default_sources:
            existing = db.query(DataSourceStatus).filter(
                DataSourceStatus.source == src["source"]
            ).first()
            if not existing:
                db.add(DataSourceStatus(**src))

        db.commit()
    finally:
        db.close()


def start_scheduler():
    """Start the APScheduler with dynamic refresh intervals."""
    init_data_source_status()

    scheduler = AsyncIOScheduler(timezone="UTC")
    refresh_mode = get_refresh_mode()
    interval_hours = get_refresh_interval_hours()

    scheduler.add_job(
        precompute_recommendations,
        CronTrigger(hour=f"*/{interval_hours}", minute=0),
        id="precompute_recommendations",
        name=f"Precompute recommendations ({refresh_mode.value}, every {interval_hours}h)",
    )

    scheduler.add_job(
        refresh_odds_data,
        CronTrigger(hour=f"*/{interval_hours}", minute=30),
        id="refresh_odds_data",
        name=f"Refresh odds data ({refresh_mode.value}, every {interval_hours}h)",
    )

    scheduler.add_job(
        refresh_player_data,
        CronTrigger(hour="6,18"),
        id="refresh_player_data",
        name="Refresh player data twice daily",
    )

    if refresh_mode == RefreshMode.NORMAL:
        scheduler.add_job(
            refresh_dongqiudi_rosters,
            CronTrigger(day_of_week="mon", hour=3),
            id="refresh_dongqiudi_rosters",
            name="Refresh Dongqiudi rosters weekly (Monday 3am)",
        )

    # Zafronix full sync: matches + standings + tournament (daily at noon CST = 4am UTC)
    scheduler.add_job(
        refresh_zafronix_results,
        CronTrigger(hour=4),
        id="refresh_zafronix_results",
        name="Zafronix full sync: matches + standings + tournament (daily noon)",
    )

    # Elo rankings from eloratings.net (daily at 5am UTC = 1pm CST, after matches update)
    scheduler.add_job(
        refresh_elo_rankings,
        CronTrigger(hour=5),
        id="refresh_elo_rankings",
        name="Elo rankings refresh from eloratings.net (daily 1pm CST)",
    )

    scheduler.start()
    print(f"APScheduler started in {refresh_mode.value} mode (refresh interval: {interval_hours}h)")

    return scheduler
