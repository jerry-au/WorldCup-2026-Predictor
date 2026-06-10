import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.team import Team
from app.models.player import Player
from app.services.dongqiudi_national_roster import (
    match_player_by_team_and_jersey,
    match_player_by_team_and_name,
    normalize_diacritics,
    try_name_reversal,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def seed_team_with_players(db, duplicate_jersey=False):
    team = Team(code="FRA", name="France", group_name="I", elo_rating=1850)
    db.add(team)
    db.flush()
    db.add(Player(team_id=team.id, name="Kylian Mbappé", jersey=10, position="FW"))
    db.add(Player(team_id=team.id, name="Mike Maignan", jersey=16, position="GK"))
    if duplicate_jersey:
        db.add(Player(team_id=team.id, name="Duplicate Ten", jersey=10, position="FW"))
    db.commit()
    return team


def seed_korea(db):
    team = Team(code="KOR", name="South Korea", group_name="A", elo_rating=1600)
    db.add(team)
    db.flush()
    # Zafronix stores Korean names as "Son Heung-min", "Lee Kang-in" (surname first)
    db.add(Player(team_id=team.id, name="Son Heung-min", jersey=None, position="FW"))
    db.add(Player(team_id=team.id, name="Lee Kang-in", jersey=None, position="MF"))
    db.add(Player(team_id=team.id, name="Kim Min-jae", jersey=None, position="DF"))
    db.commit()
    return team


def seed_diacritic_team(db):
    team = Team(code="CRO", name="Croatia", group_name="L", elo_rating=1700)
    db.add(team)
    db.flush()
    db.add(Player(team_id=team.id, name="Mateo Kovačić", jersey=11, position="MF"))
    db.add(Player(team_id=team.id, name="Josko Gvardiol", jersey=4, position="DF"))
    db.add(Player(team_id=team.id, name="Luka Sučić", jersey=21, position="MF"))
    db.commit()
    return team


# ── team + jersey ──

def test_match_player_by_team_and_jersey_success(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_jersey(db_session, team.id, 10)
    assert player is not None
    assert player.name == "Kylian Mbappé"
    assert method == "team_jersey"
    assert confidence == 1.0


def test_match_player_missing_team_returns_no_match(db_session):
    player, method, confidence = match_player_by_team_and_jersey(db_session, None, 10)
    assert player is None
    assert method == "missing_team_or_jersey"
    assert confidence == 0.0


def test_match_player_missing_jersey_returns_no_match(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_jersey(db_session, team.id, None)
    assert player is None
    assert method == "missing_team_or_jersey"
    assert confidence == 0.0


def test_match_player_no_jersey_match(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_jersey(db_session, team.id, 99)
    assert player is None
    assert method == "no_team_jersey_match"
    assert confidence == 0.0


def test_match_player_ambiguous_duplicate_jersey(db_session):
    team = seed_team_with_players(db_session, duplicate_jersey=True)
    player, method, confidence = match_player_by_team_and_jersey(db_session, team.id, 10)
    assert player is None
    assert method == "ambiguous_team_jersey"
    assert confidence == 0.0


# ── team + English name ──

def test_match_player_by_team_and_name_success(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Kylian Mbappé")
    assert player is not None
    assert player.name == "Kylian Mbappé"
    assert method == "team_en_name"
    assert confidence == 0.9


def test_match_player_by_team_and_name_case_insensitive(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "kyLIAN mBAPPÉ")
    assert player is not None
    assert player.name == "Kylian Mbappé"


def test_match_player_by_team_and_name_no_match(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Unknown Player")
    assert player is None
    assert method == "no_team_name_match"


def test_match_player_by_team_and_name_missing_team(db_session):
    player, method, confidence = match_player_by_team_and_name(db_session, None, "Mbappé")
    assert player is None
    assert method == "missing_team_or_name"


def test_match_player_by_team_and_name_missing_name(db_session):
    team = seed_team_with_players(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, None)
    assert player is None
    assert method == "missing_team_or_name"


def test_match_player_by_team_and_name_exact_priority(db_session):
    team = Team(code="BRA", name="Brazil", group_name="C", elo_rating=1840)
    db_session.add(team)
    db_session.flush()
    db_session.add(Player(team_id=team.id, name="Vinícius Júnior", jersey=7, position="FW"))
    db_session.add(Player(team_id=team.id, name="Vinícius", jersey=17, position="MF"))
    db_session.commit()
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Vinícius Júnior")
    assert player is not None
    assert player.jersey == 7


# ── diacritic normalization ──

def test_normalize_diacritics():
    assert normalize_diacritics("Mateo Kovačić") == "Mateo Kovacic"
    assert normalize_diacritics("Josko Gvardiol") == "Josko Gvardiol"
    assert normalize_diacritics("Luka Sučić") == "Luka Sucic"
    assert normalize_diacritics("Džeko") == "Dzeko"
    assert normalize_diacritics("Kylian Mbappé") == "Kylian Mbappe"


def test_match_player_diacritic_fallback(db_session):
    """Dongqiudi provides 'Mateo Kovacic' (no diacritic),
    Zafronix stores 'Mateo Kovačić' (with diacritic).  Should still match."""
    team = seed_diacritic_team(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Mateo Kovacic")
    assert player is not None
    assert player.name == "Mateo Kovačić"
    assert method.startswith("team_en_name")


def test_match_player_diacritic_fallback_reverse(db_session):
    """Dongqiudi provides 'Josko Gvardiol', Zafronix stores 'Josko Gvardiol' (same)."""
    team = seed_diacritic_team(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Josko Gvardiol")
    assert player is not None
    assert player.name == "Josko Gvardiol"


# ── name reversal for East Asian names ──

def test_try_name_reversal():
    assert try_name_reversal("Heung-min Son") == "Son Heung-min"
    assert try_name_reversal("Kang-in Lee") == "Lee Kang-in"
    assert try_name_reversal("Min-jae Kim") == "Kim Min-jae"
    assert try_name_reversal("Kylian Mbappé") is None  # Western name, no reversal


def test_match_player_korea_via_name_reversal(db_session):
    """Dongqiudi gives 'Heung-min Son', Zafronix stores 'Son Heung-min'."""
    team = seed_korea(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Heung-min Son")
    assert player is not None
    assert player.name == "Son Heung-min"


def test_match_player_korea_via_name_reversal_lee(db_session):
    """Dongqiudi gives 'Kang-in Lee', Zafronix stores 'Lee Kang-in'."""
    team = seed_korea(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Kang-in Lee")
    assert player is not None
    assert player.name == "Lee Kang-in"


def test_match_player_korea_via_name_reversal_kim(db_session):
    """Dongqiudi gives 'Min-jae Kim', Zafronix stores 'Kim Min-jae'."""
    team = seed_korea(db_session)
    player, method, confidence = match_player_by_team_and_name(db_session, team.id, "Min-jae Kim")
    assert player is not None
    assert player.name == "Kim Min-jae"
