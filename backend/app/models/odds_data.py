from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint

from ..database import Base


class Bookmaker(Base):
    __tablename__ = "bookmakers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    slug = Column(String(50), nullable=False, unique=True)
    country = Column(String(20))
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class MatchOdds(Base):
    __tablename__ = "match_odds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_a_code = Column(String(3), ForeignKey("teams.code"), nullable=False)
    team_b_code = Column(String(3), ForeignKey("teams.code"), nullable=False)
    bookmaker_id = Column(Integer, ForeignKey("bookmakers.id"), nullable=False)
    odds_win = Column(Float)
    odds_draw = Column(Float)
    odds_lose = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("team_a_code", "team_b_code", "bookmaker_id", name="uq_match_bookmaker"),
    )

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at if self.expires_at else True


class MatchOddsHistory(Base):
    __tablename__ = "match_odds_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_a_code = Column(String(3), ForeignKey("teams.code"), nullable=False, index=True)
    team_b_code = Column(String(3), ForeignKey("teams.code"), nullable=False, index=True)
    avg_odds_win = Column(Float)
    avg_odds_draw = Column(Float)
    avg_odds_lose = Column(Float)
    provider_count = Column(Integer)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class MatchOddsSummary(Base):
    __tablename__ = "match_odds_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_a_code = Column(String(3), ForeignKey("teams.code"), nullable=False)
    team_b_code = Column(String(3), ForeignKey("teams.code"), nullable=False)
    avg_odds_win = Column(Float)
    avg_odds_draw = Column(Float)
    avg_odds_lose = Column(Float)
    best_odds_win = Column(Float)
    best_odds_draw = Column(Float)
    best_odds_lose = Column(Float)
    best_win_provider = Column(String(50))
    best_draw_provider = Column(String(50))
    best_lose_provider = Column(String(50))
    provider_count = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("team_a_code", "team_b_code", name="uq_summary_match"),
    )