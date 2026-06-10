"""Scraped data from dongqiudi — stored separately from our core database.

Each record stores raw scraped data with the player detail URL for future updates.
Matches against our core Player table via English name + birthday + national team.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship

from ..database import Base


class ScrapedPlayerData(Base):
    """Raw scraped data from dongqiudi, kept separate from core player stats."""

    __tablename__ = "scraped_player_data"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Dongqiudi identifiers
    dongqiudi_player_id = Column(Integer, index=True, nullable=False)
    dongqiudi_url = Column(String(500))

    # Source league info
    source_league_code = Column(String(10), index=True)  # PL, PD, BL1, etc.
    source_league_name = Column(String(100))

    # Player info (from dongqiudi)
    name_cn = Column(String(100))          # Chinese name
    name_en = Column(String(200))          # English name (from detail page)

    # Season stats (from dongqiudi listing)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    appearances = Column(Integer, default=0)

    # Link to our DB (populated after matching)
    matched_player_id = Column(Integer, ForeignKey("players.id"), index=True, nullable=True)
    match_method = Column(String(50))       # how we matched: en_name, en_name+birth, etc.

    # Match data
    match_data_raw = Column(Text)           # JSON blob with full page stats data

    # Timestamps
    scraped_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    player = relationship("Player", backref="scraped_data")
