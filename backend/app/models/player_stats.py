from sqlalchemy import Column, Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class PlayerSeasonStats(Base):
    """Season statistics for a player at their club."""

    __tablename__ = "player_season_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    season = Column(String(10), default="2025-2026")
    competition_code = Column(String(10), index=True)  # PL, PD, BL1, etc.
    competition_name = Column(String(100))

    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    appearances = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    penalties = Column(Integer, default=0)

    # Source tracking
    source = Column(String(50), default="football-data.org")
    fetched_at = Column(String(30))

    player = relationship("Player", backref="season_stats")

    __table_args__ = (
        UniqueConstraint("player_id", "season", "competition_code", name="uq_player_season"),
    )
