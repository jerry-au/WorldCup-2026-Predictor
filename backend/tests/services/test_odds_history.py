from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.odds_data import MatchOddsHistory, MatchOddsSummary
from app.models.team import Team
from app.services.match_aggregator import build_odds_history_response
from app.services.odds import OddsClient


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_update_summary_records_average_odds_history():
    db = make_session()
    db.add_all([
        Team(code="BRA", name="Brazil"),
        Team(code="FRA", name="France"),
    ])
    db.commit()

    client = OddsClient()
    client._save_to_db(
        db,
        db.query(Team).filter(Team.code == "BRA").first(),
        db.query(Team).filter(Team.code == "FRA").first(),
        {
            "home_team": "Brazil",
            "away_team": "France",
            "bookmakers": [{
                "name": "BetExplorer",
                "slug": "betexplorer",
                "outcomes": {"Brazil": 2.1, "Draw": 3.2, "France": 3.4},
            }],
        },
    )
    db.commit()

    history = db.query(MatchOddsHistory).one()
    assert history.team_a_code == "BRA"
    assert history.team_b_code == "FRA"
    assert history.avg_odds_win == 2.1
    assert history.avg_odds_draw == 3.2
    assert history.avg_odds_lose == 3.4
    assert history.provider_count == 1


def test_update_summary_skips_history_when_average_odds_unchanged():
    db = make_session()
    db.add_all([
        Team(code="BRA", name="Brazil"),
        Team(code="FRA", name="France"),
    ])
    db.commit()

    client = OddsClient()
    odds_data = {
        "home_team": "Brazil",
        "away_team": "France",
        "bookmakers": [{
            "name": "BetExplorer",
            "slug": "betexplorer",
            "outcomes": {"Brazil": 2.1, "Draw": 3.2, "France": 3.4},
        }],
    }
    team_a = db.query(Team).filter(Team.code == "BRA").first()
    team_b = db.query(Team).filter(Team.code == "FRA").first()

    client._save_to_db(db, team_a, team_b, odds_data)
    client._save_to_db(db, team_a, team_b, odds_data)
    db.commit()

    assert db.query(MatchOddsHistory).count() == 1


def test_build_odds_history_response_resolves_match_and_orders_points():
    db = make_session()
    db.add_all([
        Team(code="BRA", name="Brazil"),
        Team(code="FRA", name="France"),
        MatchOddsHistory(
            team_a_code="BRA",
            team_b_code="FRA",
            avg_odds_win=2.2,
            avg_odds_draw=3.3,
            avg_odds_lose=3.5,
            provider_count=2,
            recorded_at=datetime(2026, 6, 16, 10, 0),
        ),
        MatchOddsHistory(
            team_a_code="BRA",
            team_b_code="FRA",
            avg_odds_win=2.0,
            avg_odds_draw=3.1,
            avg_odds_lose=3.8,
            provider_count=2,
            recorded_at=datetime(2026, 6, 16, 9, 0),
        ),
        MatchOddsSummary(
            team_a_code="BRA",
            team_b_code="FRA",
            avg_odds_win=2.4,
            avg_odds_draw=3.4,
            avg_odds_lose=3.2,
            best_odds_win=2.5,
            best_odds_draw=3.5,
            best_odds_lose=3.3,
            provider_count=3,
            updated_at=datetime(2026, 6, 16, 11, 0),
        ),
    ])
    db.commit()

    response = build_odds_history_response(db, "BRA-FRA", "BRA", "FRA")

    assert response == {
        "match_id": "BRA-FRA",
        "home_code": "BRA",
        "away_code": "FRA",
        "latest_odds": {
            "avg_win": 2.4,
            "avg_draw": 3.4,
            "avg_lose": 3.2,
            "best_win": 2.5,
            "best_draw": 3.5,
            "best_lose": 3.3,
            "best_win_provider": None,
            "best_draw_provider": None,
            "best_lose_provider": None,
            "provider_count": 3,
            "updated_at": "2026-06-16T11:00:00",
        },
        "points": [
            {
                "recorded_at": "2026-06-16T09:00:00",
                "avg_win": 2.0,
                "avg_draw": 3.1,
                "avg_lose": 3.8,
                "provider_count": 2,
            },
            {
                "recorded_at": "2026-06-16T10:00:00",
                "avg_win": 2.2,
                "avg_draw": 3.3,
                "avg_lose": 3.5,
                "provider_count": 2,
            },
        ],
    }
