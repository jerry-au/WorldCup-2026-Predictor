"""Dongqiudi match results model — crawled from Dongqiudi World Cup schedule."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint

from ..database import Base


class DongqiudiMatch(Base):
    """Match results scraped from Dongqiudi World Cup schedule page."""
    __tablename__ = "dongqiudi_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(String(50), unique=True, nullable=False, index=True)
    stage = Column(String(50))           # group_stage, round_of_16, quarter, semi, final
    group_name = Column(String(10))       # group letter for group stage matches
    team_home_code = Column(String(3))    # matched to Team.code
    team_away_code = Column(String(3))
    team_home_name_cn = Column(String(100))  # Chinese name from Dongqiudi
    team_away_name_cn = Column(String(100))
    score_home = Column(Integer)           # regular time score
    score_away = Column(Integer)
    score_home_et = Column(Integer)        # extra time score
    score_away_et = Column(Integer)
    home_penalties = Column(Integer)       # penalty shootout
    away_penalties = Column(Integer)
    status = Column(String(20), default="completed")  # completed, upcoming, live
    commence_time = Column(DateTime)
    stadium = Column(String(200))
    raw_data = Column(Text)                # full response for flexibility
    scraped_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("match_id", name="uq_dqd_match"),
    )
