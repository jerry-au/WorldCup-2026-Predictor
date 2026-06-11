from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(3), unique=True, index=True, nullable=False)  # MEX, BRA
    name = Column(String(100), nullable=False)
    iso = Column(String(2))
    confederation = Column(String(30))
    group_name = Column(String(2), index=True)
    flag_url = Column(String(500))
    coach_name = Column(String(100))
    coach_country = Column(String(100))
    elo_rating = Column(Float, default=1500.0)
    fifa_rank = Column(Integer, default=0)
    market_value_eur = Column(Float, default=0.0)

    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")
