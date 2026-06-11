from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship

from ..database import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    jersey = Column(Integer, nullable=True)
    position = Column(String(5))  # GK, DF, MF, FW
    birth_date = Column(Date)
    age_at_tournament = Column(Integer)
    club_name = Column(String(200))
    club_country = Column(String(100))
    is_captain = Column(Boolean, default=False)
    goals = Column(Integer, default=0)

    team = relationship("Team", back_populates="players")
