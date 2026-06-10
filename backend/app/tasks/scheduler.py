"""Data sync scheduler for API quota management.

Implements the scheduling strategy defined in the design doc:

The Odds API (500 req/month):
  - Match day (today): refresh every 8h
  - Match day (tomorrow/today+2): refresh 1x/day
  - Others: no refresh

Zafronix (250 req/day):
  - Match day during play: refresh every 15 min
  - Standings: refresh 1x after each group match finishes
  - Non-match day: no refresh
"""

from datetime import datetime, date, timedelta
from enum import Enum


class MatchBucket(Enum):
    TODAY = "today"           # 今天比赛 → 8h 更新
    SOON = "soon"             # 明后天比赛 → 1x/天
    LATER = "later"           # 其他比赛 → 不更新
    NOT_MATCHDAY = "off"      # 无比赛日


def get_match_bucket(
    match_date: date, today: date | None = None
) -> MatchBucket:
    """Classify a match into its update priority bucket."""
    if today is None:
        today = date.today()

    days_until = (match_date - today).days

    if days_until < 0:
        return MatchBucket.LATER           # 已结束
    elif days_until == 0:
        return MatchBucket.TODAY           # 今天
    elif days_until <= 2:
        return MatchBucket.SOON            # 明后天
    else:
        return MatchBucket.LATER           # 更晚


def is_matchday(today: date | None = None) -> bool:
    """Check if today is a World Cup match day."""
    # 2026 WC: 2026-06-11 to 2026-07-19
    if today is None:
        today = date.today()
    start = date(2026, 6, 11)
    end = date(2026, 7, 19)
    return start <= today <= end


def needs_odds_refresh(
    last_refresh: datetime | None,
    match_date: date,
    today: date | None = None,
) -> bool:
    """Determine if odds need refreshing based on match bucket."""
    bucket = get_match_bucket(match_date, today)
    now = datetime.now()

    if bucket == MatchBucket.TODAY:
        # Refresh every 8 hours
        if last_refresh is None:
            return True
        hours_since = (now - last_refresh).total_seconds() / 3600
        return hours_since >= 8

    elif bucket == MatchBucket.SOON:
        # Refresh once per day
        if last_refresh is None:
            return True
        today_date = today or date.today()
        return last_refresh.date() < today_date

    else:
        return False


def needs_result_refresh(
    last_refresh: datetime | None,
    is_live: bool,
) -> bool:
    """Determine if Zafronix results need refreshing.

    Only refreshes during match play (every 15 min).
    """
    if not is_live:
        return False
    if last_refresh is None:
        return True
    minutes_since = (datetime.now() - last_refresh).total_seconds() / 60
    return minutes_since >= 15


def needs_standings_refresh(
    last_refresh: datetime | None,
    match_just_finished: bool,
) -> bool:
    """Refresh standings only after a match finishes."""
    if match_just_finished:
        return True
    return False


import json
from datetime import datetime, timedelta

from ..database import SessionLocal
from ..models.team import Team
from ..models.recommendation_cache import RecommendationCache
from ..core.prediction import PredictionEngine
from ..services.recommendation import recommendation_engine


def precompute_recommendations():
    """Precompute value bets and discrepancies for all same-group matchups.

    Results are cached in the recommendation_cache table with 8h TTL.
    Note: This runs synchronously and does not fetch live odds (uses cached/empty).
    """
    db = SessionLocal()
    try:
        engine = PredictionEngine()
        teams = db.query(Team).all()
        ttl = RecommendationCache.default_ttl()

        scanned = 0
        for i, team_a in enumerate(teams):
            for j, team_b in enumerate(teams):
                if j <= i or team_a.group_name != team_b.group_name:
                    continue
                if scanned >= 12:
                    break

                pred = engine.predict(team_a, team_b, "group")

                # Use empty odds_data for precomputation (no live API call)
                betting = recommendation_engine.analyze(
                    system_probs=pred["probabilities"],
                    system_confidence=pred["system_confidence"],
                    odds_data=None,
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
    finally:
        db.close()


def _upsert_cache(db, cache_type, team_a_code, team_b_code, result_data, computed_at, expires_at):
    """Insert or update a cache entry."""
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
