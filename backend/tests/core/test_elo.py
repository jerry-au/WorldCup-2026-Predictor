from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.elo import update_elo, update_team_elos_from_completed_matches
from app.database import Base
from app.models.team import Team
from app.models.zafronix_data import ZafronixMatch


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_update_team_elos_from_completed_matches_updates_team_ratings():
    db = make_session()
    db.add_all([
        Team(code="BRA", name="Brazil", elo_rating=1800.0),
        Team(code="FRA", name="France", elo_rating=1700.0),
        ZafronixMatch(
            match_id="BRA-FRA-1",
            team_home_code="BRA",
            team_away_code="FRA",
            score_home=2,
            score_away=1,
            status="completed",
            commence_time=datetime(2026, 6, 11, 20, 0),
        ),
        ZafronixMatch(
            match_id="BRA-FRA-UPCOMING",
            team_home_code="BRA",
            team_away_code="FRA",
            score_home=0,
            score_away=0,
            status="upcoming",
            commence_time=datetime(2026, 6, 12, 20, 0),
        ),
    ])
    db.commit()

    expected_bra, expected_fra = update_elo(1800.0, 1700.0, 1.0)

    updated_count = update_team_elos_from_completed_matches(db)
    bra = db.query(Team).filter(Team.code == "BRA").first()
    fra = db.query(Team).filter(Team.code == "FRA").first()

    assert updated_count == 1
    assert bra.elo_rating == expected_bra
    assert fra.elo_rating == expected_fra


def test_update_team_elos_from_completed_matches_uses_draw_score():
    db = make_session()
    db.add_all([
        Team(code="ARG", name="Argentina", elo_rating=1850.0),
        Team(code="GER", name="Germany", elo_rating=1750.0),
        ZafronixMatch(
            match_id="ARG-GER-1",
            team_home_code="ARG",
            team_away_code="GER",
            score_home=1,
            score_away=1,
            status="completed",
        ),
    ])
    db.commit()

    expected_arg, expected_ger = update_elo(1850.0, 1750.0, 0.5)

    updated_count = update_team_elos_from_completed_matches(db)
    arg = db.query(Team).filter(Team.code == "ARG").first()
    ger = db.query(Team).filter(Team.code == "GER").first()

    assert updated_count == 1
    assert arg.elo_rating == expected_arg
    assert ger.elo_rating == expected_ger
