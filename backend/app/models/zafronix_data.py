"""Zafronix World Cup data models — cached from API into local SQLite."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, UniqueConstraint

from ..database import Base


class ZafronixMatch(Base):
    """Cached match results from Zafronix /v1/matches."""
    __tablename__ = "zafronix_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), unique=True, nullable=False)
    tournament_year = Column(Integer, default=2026)
    stage = Column(String(50))          # group_stage, round_of_32, ...
    group_name = Column(String(10))
    team_home_code = Column(String(3))
    team_away_code = Column(String(3))
    team_home_name = Column(String(100))
    team_away_name = Column(String(100))
    score_home = Column(Integer)
    score_away = Column(Integer)
    score_home_et = Column(Integer)      # extra time (if any)
    score_away_et = Column(Integer)
    home_penalties = Column(Integer)     # shootout (if any)
    away_penalties = Column(Integer)
    status = Column(String(20), default="completed")  # completed, upcoming, live
    commence_time = Column(DateTime)
    stadium = Column(String(200))
    attendance = Column(Integer)
    referee = Column(String(200))
    raw_data = Column(JSON)             # full API response for flexibility
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("match_id", name="uq_zaf_match"),
    )


class ZafronixStanding(Base):
    """Cached group standings from Zafronix /v1/standings."""
    __tablename__ = "zafronix_standings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_year = Column(Integer, default=2026)
    group_name = Column(String(10), nullable=False)
    position = Column(Integer, nullable=False)
    team_code = Column(String(3), nullable=False)
    team_name = Column(String(100))
    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_diff = Column(Integer, default=0)
    points = Column(Integer, default=0)
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tournament_year", "group_name", "team_code",
                         name="uq_zaf_standing"),
    )


class ZafronixTournament(Base):
    """Cached full tournament data from Zafronix /v1/tournaments/{year}."""
    __tablename__ = "zafronix_tournament"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_year = Column(Integer, unique=True, default=2026)
    host_country = Column(String(200))
    champion_team_code = Column(String(3))
    runner_up_code = Column(String(3))
    total_teams = Column(Integer)
    total_matches = Column(Integer)
    total_goals = Column(Integer)
    raw_data = Column(JSON)             # brackets, awards, squads, etc.
    fetched_at = Column(DateTime, default=datetime.utcnow)
