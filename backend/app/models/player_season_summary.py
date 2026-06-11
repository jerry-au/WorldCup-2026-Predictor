"""Dongqiudi player season summary model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from ..database import Base


class DongqiudiPlayerSeasonSummary(Base):
    """Season-level player stats from Dongqiudi career-stats API."""

    __tablename__ = "dongqiudi_player_season_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dongqiudi_player_id = Column(
        Integer, ForeignKey("dongqiudi_players.id"), nullable=False, index=True
    )
    matched_player_id = Column(Integer, ForeignKey("players.id"), nullable=True, index=True)

    category = Column(String(20), nullable=False)  # total / league / cup / national
    season = Column(String(20), nullable=False)
    club_name = Column(String(100), nullable=False)
    competition_name = Column(String(100), nullable=True)

    appearances = Column(Integer, default=0)
    starts = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)

    scraped_at = Column(DateTime, server_default=func.now())

    dongqiudi_player = relationship("DongqiudiPlayerData", backref="season_summaries")
    matched_player = relationship("Player")

    __table_args__ = (
        UniqueConstraint(
            "dongqiudi_player_id",
            "category",
            "season",
            "club_name",
            "competition_name",
            name="uq_dqd_player_season_summary",
        ),
    )
