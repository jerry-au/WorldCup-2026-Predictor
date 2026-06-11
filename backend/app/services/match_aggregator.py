from datetime import UTC, date, datetime, timedelta, time
from sqlalchemy.orm import Session
from ..core.prediction import PredictionEngine
from ..models.odds_data import MatchOddsSummary
from ..models.team import Team
from ..models.dongqiudi_match import DongqiudiMatch

engine = PredictionEngine()
CACHE_TTL_SECONDS = 300


def build_today_matches_response(db: Session, target_date: date | None = None) -> dict:
    if target_date is None:
        target_date = date.today()
    matches = _query_matches_for_date(db, target_date)
    items = [_build_match_item(db, match) for match in matches]
    updated_candidates = [match.scraped_at for match in matches if getattr(match, "scraped_at", None)]
    return {
        "matches": items,
        "total": len(items),
        "cache": {
            "updated_at": max(updated_candidates).isoformat() if updated_candidates else datetime.now(UTC).isoformat(),
            "ttl_seconds": CACHE_TTL_SECONDS,
        },
    }


def _query_matches_for_date(db: Session, target_date: date) -> list[DongqiudiMatch]:
    # 北京时间当天 09:00 = UTC 当天 01:00，窗口为 24 小时
    start = datetime.combine(target_date, time(1, 0, 0))
    end = start + timedelta(hours=24)
    matches = (
        db.query(DongqiudiMatch)
        .filter(DongqiudiMatch.commence_time >= start)
        .filter(DongqiudiMatch.commence_time < end)
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
            .order_by(ZafronixMatch.commence_time.asc())
            .all()
        )

    return matches


def _build_match_item(db: Session, match) -> dict:
    team_a = db.query(Team).filter(Team.code == match.team_home_code).first()
    team_b = db.query(Team).filter(Team.code == match.team_away_code).first()
    prediction = None
    if team_a and team_b:
        pred = engine.predict(team_a, team_b, _normalize_match_type(match.stage))
        probs = pred["probabilities"]
        prediction = {
            "win": probs["win"],
            "draw": probs["draw"],
            "lose": probs["lose"],
            "system_confidence": pred["system_confidence"],
        }
    odds = _get_odds_summary(db, match.team_home_code, match.team_away_code)
    return {
        "match_id": match.match_id,
        "home": {
            "code": match.team_home_code,
            "name": team_a.name if team_a else match.team_home_name_cn,
            "name_cn": team_a.name_cn if team_a else None,
            "flag_url": f"/static/images/{team_a.local_flag_path}" if (team_a and team_a.local_flag_path) else (team_a.flag_url if team_a else None),
        },
        "away": {
            "code": match.team_away_code,
            "name": team_b.name if team_b else match.team_away_name_cn,
            "name_cn": team_b.name_cn if team_b else None,
            "flag_url": f"/static/images/{team_b.local_flag_path}" if (team_b and team_b.local_flag_path) else (team_b.flag_url if team_b else None),
        },
        "stage": match.stage,
        "group_name": match.group_name,
        "commence_time": match.commence_time.isoformat() if match.commence_time else None,
        "prediction": prediction,
        "odds": odds,
    }


def _normalize_match_type(stage: str | None) -> str:
    return "group" if not stage or "group" in stage else "knockout"


def _get_odds_summary(db: Session, team_a_code: str | None, team_b_code: str | None) -> dict | None:
    if not team_a_code or not team_b_code:
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
