from datetime import date, datetime, timedelta, time, timezone

# Python 3.10 兼容：datetime.UTC 是 3.11+ 才有的
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from pathlib import Path
from sqlalchemy.orm import Session
from ..core.prediction import PredictionEngine
from ..models.odds_data import MatchOddsHistory, MatchOddsSummary
from ..models.team import Team
from ..models.dongqiudi_match import DongqiudiMatch
from ..models.dongqiudi_data import DongqiudiTeamData

engine = PredictionEngine()
CACHE_TTL_SECONDS = 300
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "images"


def _resolve_flag_url(team: Team | None) -> str | None:
    """解析国旗URL：本地文件存在则用本地路径，否则用CDN"""
    if not team:
        return None
    if team.flag_url:
        return team.flag_url
    if team.local_flag_path:
        local_path = STATIC_DIR / team.local_flag_path
        if local_path.exists():
            return f"/static/images/{team.local_flag_path}"
    return None


def _resolve_team_name_cn(db: Session, team: Team | None, code: str, fallback_cn: str | None = None) -> str | None:
    """解析球队中文名：teams.name_cn → dongqiudi_teams.name_cn → fallback → None"""
    if team and team.name_cn:
        return team.name_cn
    dqd = db.query(DongqiudiTeamData).filter(DongqiudiTeamData.matched_team_code == code).first()
    if dqd and dqd.name_cn:
        return dqd.name_cn
    return fallback_cn


def _batch_preload_teams_and_odds(db: Session, matches) -> tuple[dict, dict]:
    """批量预加载：收集所有涉及的 team_code，一次性查询 Team 和 OddsSummary。"""
    codes: set[str] = set()
    for m in matches:
        codes.add(m.team_home_code)
        codes.add(m.team_away_code)
    if not codes:
        return {}, {}
    teams = {t.code: t for t in db.query(Team).filter(Team.code.in_(codes)).all()}
    odds_map: dict[tuple, MatchOddsSummary] = {}
    summaries = db.query(MatchOddsSummary).filter(
        MatchOddsSummary.team_a_code.in_(codes),
        MatchOddsSummary.team_b_code.in_(codes),
    ).all()
    for s in summaries:
        odds_map[(s.team_a_code, s.team_b_code)] = s
    return teams, odds_map


def build_today_matches_response(db: Session, target_date: date | None = None) -> dict:
    if target_date is None:
        target_date = date.today()
    matches = _query_matches_for_date(db, target_date)
    teams, odds_map = _batch_preload_teams_and_odds(db, matches)
    items = [_build_match_item(db, match, teams, odds_map) for match in matches]
    updated_candidates = [match.scraped_at for match in matches if getattr(match, "scraped_at", None)]
    return {
        "matches": items,
        "total": len(items),
        "cache": {
            "updated_at": max(updated_candidates).isoformat() if updated_candidates else datetime.now(UTC).isoformat(),
            "ttl_seconds": CACHE_TTL_SECONDS,
        },
    }


def build_all_matches_response(db: Session, stage: str | None = None, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    """获取所有比赛赛程，包括已结束比赛的比分（支持分页）"""
    query = db.query(DongqiudiMatch)

    if stage:
        query = query.filter(DongqiudiMatch.stage == stage)
    if status:
        query = query.filter(DongqiudiMatch.status == status)

    if status == "completed":
        query = query.order_by(DongqiudiMatch.commence_time.desc())
    else:
        query = query.order_by(DongqiudiMatch.commence_time.asc())

    # 获取总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    matches = query.offset(offset).limit(page_size).all()

    teams, odds_map = _batch_preload_teams_and_odds(db, matches)
    items = [_build_full_match_item(db, match, teams, odds_map) for match in matches]

    return {
        "matches": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "cache": {
            "updated_at": datetime.now(UTC).isoformat(),
            "ttl_seconds": CACHE_TTL_SECONDS,
        },
    }


def _query_matches_for_date(
    db: Session,
    target_date: date,
    now: datetime | None = None,
) -> list[DongqiudiMatch]:
    start = datetime.combine(target_date, time(0, 0, 0))
    end = start + timedelta(hours=48)
    min_commence_time = (now or datetime.now()) - timedelta(hours=2)
    matches = (
        db.query(DongqiudiMatch)
        .filter(DongqiudiMatch.commence_time >= start)
        .filter(DongqiudiMatch.commence_time < end)
        .filter(DongqiudiMatch.commence_time > min_commence_time)
        .filter(DongqiudiMatch.status != "completed")
        .order_by(DongqiudiMatch.commence_time.asc())
        .all()
    )

    # Fallback to Zafronix if no Dongqiudi data
    if not matches:
        from ..models.zafronix_data import ZafronixMatch
        matches = (
            db.query(ZafronixMatch)
            .filter(ZafronixMatch.commence_time >= start)
            .filter(ZafronixMatch.commence_time < end)
            .filter(ZafronixMatch.commence_time > min_commence_time)
            .filter(ZafronixMatch.status != "completed")
            .order_by(ZafronixMatch.commence_time.asc())
            .all()
        )

    return matches


def _build_match_item(
    db: Session, match,
    teams: dict[str, Team] | None = None,
    odds_cache: dict | None = None,
) -> dict:
    if teams is None:
        team_a = db.query(Team).filter(Team.code == match.team_home_code).first()
        team_b = db.query(Team).filter(Team.code == match.team_away_code).first()
    else:
        team_a = teams.get(match.team_home_code)
        team_b = teams.get(match.team_away_code)
    prediction = None
    if team_a and team_b:
        pred = engine.predict(team_a, team_b, db=db, match_type=_normalize_match_type(match.stage))
        probs = pred["probabilities"]
        prediction = {
            "win": probs["win"],
            "draw": probs["draw"],
            "lose": probs["lose"],
            "system_confidence": pred["system_confidence"],
        }
    odds = _get_odds_summary(db, match.team_home_code, match.team_away_code, odds_cache)
    return {
        "match_id": match.match_id,
        "home": {
            "code": match.team_home_code,
            "name": team_a.name if team_a else match.team_home_name_cn,
            "name_cn": _resolve_team_name_cn(db, team_a, match.team_home_code, getattr(match, 'team_home_name_cn', None)),
            "flag_url": _resolve_flag_url(team_a),
        },
        "away": {
            "code": match.team_away_code,
            "name": team_b.name if team_b else match.team_away_name_cn,
            "name_cn": _resolve_team_name_cn(db, team_b, match.team_away_code, getattr(match, 'team_away_name_cn', None)),
            "flag_url": _resolve_flag_url(team_b),
        },
        "stage": match.stage,
        "group_name": match.group_name,
        "commence_time": match.commence_time.isoformat() if match.commence_time else None,
        "prediction": prediction,
        "odds": odds,
    }


def _build_full_match_item(
    db: Session, match,
    teams: dict[str, Team] | None = None,
    odds_cache: dict | None = None,
) -> dict:
    """构建完整的比赛数据，包括比分"""
    if teams is None:
        team_a = db.query(Team).filter(Team.code == match.team_home_code).first()
        team_b = db.query(Team).filter(Team.code == match.team_away_code).first()
    else:
        team_a = teams.get(match.team_home_code)
        team_b = teams.get(match.team_away_code)

    # 构建比分信息
    score = None
    if match.status == "completed" and match.score_home is not None:
        score = {
            "home": match.score_home,
            "away": match.score_away,
        }
        # 加时赛比分
        if match.score_home_et is not None:
            score["home_et"] = match.score_home_et
            score["away_et"] = match.score_away_et
        # 点球大战
        if match.home_penalties is not None:
            score["home_penalties"] = match.home_penalties
            score["away_penalties"] = match.away_penalties

    # 只为未完成的比赛生成预测
    prediction = None
    if match.status != "completed" and team_a and team_b:
        pred = engine.predict(team_a, team_b, db=db, match_type=_normalize_match_type(match.stage))
        probs = pred["probabilities"]
        prediction = {
            "win": probs["win"],
            "draw": probs["draw"],
            "lose": probs["lose"],
            "system_confidence": pred["system_confidence"],
        }

    odds = _get_odds_summary(db, match.team_home_code, match.team_away_code, odds_cache)

    return {
        "match_id": match.match_id,
        "home": {
            "code": match.team_home_code,
            "name": team_a.name if team_a else match.team_home_name_cn,
            "name_cn": _resolve_team_name_cn(db, team_a, match.team_home_code, getattr(match, 'team_home_name_cn', None)),
            "flag_url": _resolve_flag_url(team_a),
        },
        "away": {
            "code": match.team_away_code,
            "name": team_b.name if team_b else match.team_away_name_cn,
            "name_cn": _resolve_team_name_cn(db, team_b, match.team_away_code, getattr(match, 'team_away_name_cn', None)),
            "flag_url": _resolve_flag_url(team_b),
        },
        "stage": match.stage,
        "group_name": match.group_name,
        "commence_time": match.commence_time.isoformat() if match.commence_time else None,
        "status": match.status,
        "stadium": match.stadium,
        "score": score,
        "prediction": prediction,
        "odds": odds,
    }


def _normalize_match_type(stage: str | None) -> str:
    return "group" if not stage or "group" in stage else "knockout"


def build_odds_history_response(
    db: Session,
    match_id: str,
    home_code: str,
    away_code: str,
) -> dict:
    points = (
        db.query(MatchOddsHistory)
        .filter(MatchOddsHistory.team_a_code == home_code)
        .filter(MatchOddsHistory.team_b_code == away_code)
        .order_by(MatchOddsHistory.recorded_at.asc())
        .all()
    )
    if not points:
        points = (
            db.query(MatchOddsHistory)
            .filter(MatchOddsHistory.team_a_code == away_code)
            .filter(MatchOddsHistory.team_b_code == home_code)
            .order_by(MatchOddsHistory.recorded_at.asc())
            .all()
        )
        return {
            "match_id": match_id,
            "home_code": home_code,
            "away_code": away_code,
            "latest_odds": _get_odds_summary(db, home_code, away_code),
            "points": [_reverse_history_point(point) for point in points],
        }

    return {
        "match_id": match_id,
        "home_code": home_code,
        "away_code": away_code,
        "latest_odds": _get_odds_summary(db, home_code, away_code),
        "points": [_history_point(point) for point in points],
    }


def _history_point(point: MatchOddsHistory) -> dict:
    return {
        "recorded_at": point.recorded_at.isoformat() if point.recorded_at else None,
        "avg_win": point.avg_odds_win,
        "avg_draw": point.avg_odds_draw,
        "avg_lose": point.avg_odds_lose,
        "provider_count": point.provider_count,
    }


def _reverse_history_point(point: MatchOddsHistory) -> dict:
    return {
        "recorded_at": point.recorded_at.isoformat() if point.recorded_at else None,
        "avg_win": point.avg_odds_lose,
        "avg_draw": point.avg_odds_draw,
        "avg_lose": point.avg_odds_win,
        "provider_count": point.provider_count,
    }


def _get_odds_summary(
    db: Session, team_a_code: str | None, team_b_code: str | None,
    cache: dict | None = None,
) -> dict | None:
    if not team_a_code or not team_b_code:
        return None
    if cache is not None:
        summary = cache.get((team_a_code, team_b_code))
        if summary:
            return _forward_odds(summary)
        summary = cache.get((team_b_code, team_a_code))
        if summary:
            return _reverse_odds(summary)
        return None
    summary = (
        db.query(MatchOddsSummary)
        .filter(MatchOddsSummary.team_a_code == team_a_code)
        .filter(MatchOddsSummary.team_b_code == team_b_code)
        .first()
    )
    if not summary:
        summary = (
            db.query(MatchOddsSummary)
            .filter(MatchOddsSummary.team_a_code == team_b_code)
            .filter(MatchOddsSummary.team_b_code == team_a_code)
            .first()
        )
        if not summary:
            return None
        return _reverse_odds(summary)
    return _forward_odds(summary)


def _forward_odds(summary: MatchOddsSummary) -> dict:
    return {
        "avg_win": summary.avg_odds_win,
        "avg_draw": summary.avg_odds_draw,
        "avg_lose": summary.avg_odds_lose,
        "best_win": summary.best_odds_win,
        "best_draw": summary.best_odds_draw,
        "best_lose": summary.best_odds_lose,
        "best_win_provider": summary.best_win_provider,
        "best_draw_provider": summary.best_draw_provider,
        "best_lose_provider": summary.best_lose_provider,
        "provider_count": summary.provider_count,
        "updated_at": summary.updated_at.isoformat() if summary.updated_at else None,
    }


def _reverse_odds(summary: MatchOddsSummary) -> dict:
    return {
        "avg_win": summary.avg_odds_lose,
        "avg_draw": summary.avg_odds_draw,
        "avg_lose": summary.avg_odds_win,
        "best_win": summary.best_odds_lose,
        "best_draw": summary.best_odds_draw,
        "best_lose": summary.best_odds_win,
        "best_win_provider": summary.best_lose_provider,
        "best_draw_provider": summary.best_draw_provider,
        "best_lose_provider": summary.best_win_provider,
        "provider_count": summary.provider_count,
        "updated_at": summary.updated_at.isoformat() if summary.updated_at else None,
    }
