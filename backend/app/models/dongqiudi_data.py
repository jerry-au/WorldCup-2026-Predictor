from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from ..database import Base
from ..models.team import Team


class DongqiudiTeamData(Base):
    __tablename__ = "dongqiudi_teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dongqiudi_team_id = Column(String(30), unique=True, index=True, nullable=False)
    team_url = Column(String(500))
    name_cn = Column(String(100))
    name_en = Column(String(100))

    matched_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    matched_team_code = Column(String(3), nullable=True, index=True)
    match_method = Column(String(50))

    raw_data = Column(Text)
    scraped_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    matched_team = relationship("Team")
    coaches = relationship("DongqiudiCoachData", back_populates="team", cascade="all, delete-orphan")
    players = relationship("DongqiudiPlayerData", back_populates="team", cascade="all, delete-orphan")


class DongqiudiCoachData(Base):
    __tablename__ = "dongqiudi_coaches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dongqiudi_team_data_id = Column(Integer, ForeignKey("dongqiudi_teams.id"), nullable=False, index=True)

    person_id = Column(String(30), index=True, nullable=False)
    person_name = Column(String(100))
    person_logo = Column(String(500))
    age_text = Column(String(30))
    nationality_name = Column(String(100))
    role_type = Column(String(100))
    scheme = Column(String(500))
    profile_url = Column(String(500))

    raw_data = Column(Text)
    scraped_at = Column(DateTime, server_default=func.now())

    team = relationship("DongqiudiTeamData", back_populates="coaches")

    __table_args__ = (
        UniqueConstraint("dongqiudi_team_data_id", "person_id", "role_type", name="uq_dqd_coach_team_person_role"),
    )


class DongqiudiPlayerData(Base):
    __tablename__ = "dongqiudi_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dongqiudi_team_data_id = Column(Integer, ForeignKey("dongqiudi_teams.id"), nullable=False, index=True)

    person_id = Column(String(30), index=True, nullable=False)
    person_name = Column(String(100))
    person_en_name = Column(String(200))
    person_logo = Column(String(500))
    local_photo_path = Column(String(200))
    jersey_number = Column(Integer, nullable=True)
    age_text = Column(String(30))
    club_name_cn = Column(String(100))
    position_group = Column(String(50))
    position_type = Column(String(50))
    weekly_salary = Column(String(50))

    appearances = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    market_value_text = Column(String(50))

    scheme = Column(String(500))
    profile_url = Column(String(500))
    stats_raw = Column(Text)
    raw_data = Column(Text)

    matched_player_id = Column(Integer, ForeignKey("players.id"), nullable=True, index=True)
    match_method = Column(String(50))
    match_confidence = Column(Float, default=0.0)

    scraped_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    team = relationship("DongqiudiTeamData", back_populates="players")
    matched_player = relationship("Player")

    __table_args__ = (
        UniqueConstraint("dongqiudi_team_data_id", "person_id", name="uq_dqd_player_team_person"),
    )
