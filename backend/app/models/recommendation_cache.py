"""Cache for precomputed betting recommendations."""

from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint

from ..database import Base


class RecommendationCache(Base):
    __tablename__ = "recommendation_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_type = Column(String(20), nullable=False)  # 'value_bets' | 'discrepancies'
    team_a_code = Column(String(3), nullable=False)
    team_b_code = Column(String(3), nullable=False)
    result_data = Column(Text, nullable=False)  # JSON string
    computed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("cache_type", "team_a_code", "team_b_code", name="uq_cache_type_teams"),
    )

    @staticmethod
    def default_ttl() -> timedelta:
        return timedelta(hours=8)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at if self.expires_at else True
