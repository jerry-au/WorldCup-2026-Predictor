"""Dongqiudi player ability (综合能力) model.

Stores FIFA-style player ability ratings scraped from Dongqiudi:
- Overall rating and hexagon radar stats (pace, shooting, passing, dribbling, defending, physical)
- Star skills (international reputation, weak foot, skill moves)
- Detailed bar info across 7 categories
- Position ratings for all positions
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class DongqiudiPlayerAbility(Base):
    """Player overall ability ratings from Dongqiudi sofifa API."""

    __tablename__ = "dongqiudi_player_abilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dongqiudi_player_id = Column(
        Integer, ForeignKey("dongqiudi_players.id"), nullable=False, index=True
    )
    matched_player_id = Column(Integer, ForeignKey("players.id"), nullable=True, index=True)

    ability_id = Column(String(30), nullable=False, index=True)
    overall = Column(Integer, default=0)  # 综合能力
    pace = Column(Integer, default=0)  # 速度
    shooting = Column(Integer, default=0)  # 射门
    passing = Column(Integer, default=0)  # 传球
    dribbling = Column(Integer, default=0)  # 盘带
    defending = Column(Integer, default=0)  # 防守
    physical = Column(Integer, default=0)  # 力量

    star_skills = Column(Text)  # 星级技能 JSON
    position_ratings = Column(Text)  # 位置评分 JSON
    bar_info = Column(Text)  # 7大类详细能力 JSON

    foot = Column(String(10))  # 惯用脚
    registered_position = Column(String(50))  # 注册位置
    version = Column(String(50))  # FC 版本
    last_grab_time = Column(String(50))  # 数据抓取时间

    raw_data = Column(Text)  # 原始API响应JSON

    scraped_at = Column(DateTime, server_default=func.now())

    dongqiudi_player = relationship("DongqiudiPlayerData", backref="ability")
    matched_player = relationship("Player")

    __table_args__ = (
        UniqueConstraint(
            "dongqiudi_player_id", name="uq_dqd_player_ability"
        ),
    )
