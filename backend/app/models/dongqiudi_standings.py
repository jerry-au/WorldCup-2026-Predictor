"""Dongqiudi group standings model — crawled from Dongqiudi World Cup standings page."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint

from ..database import Base


class DongqiudiStanding(Base):
    """Group standings scraped from Dongqiudi World Cup standings page."""
    __tablename__ = "dongqiudi_standings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tournament_year = Column(Integer, default=2026)
    group_name = Column(String(10), nullable=False)
    position = Column(Integer, nullable=False)
    team_code = Column(String(3), nullable=False, index=True)  # matched to Team.code
    team_name_cn = Column(String(100))  # Chinese name from Dongqiudi
    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    goal_diff = Column(Integer, default=0)
    points = Column(Integer, default=0)
    raw_data = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tournament_year", "group_name", "team_code",
                         name="uq_dqd_standing"),
    )
