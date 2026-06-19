"""Simulation run & result models for Monte Carlo tournament simulation."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text

from ..database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String(36), primary_key=True)
    status = Column(String(20), nullable=False, default="pending")  # pending|running|completed|failed
    total_iterations = Column(Integer, default=10000)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("simulation_runs.id"), nullable=False, index=True)
    team_code = Column(String(3), nullable=False)
    team_name = Column(String(100), nullable=False)
    round_32 = Column(Float, default=0.0)
    round_16 = Column(Float, default=0.0)
    quarter = Column(Float, default=0.0)
    semi = Column(Float, default=0.0)
    final_ = Column(Float, default=0.0)
    champion = Column(Float, default=0.0)


class KnockoutBracket(Base):
    __tablename__ = "knockout_brackets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), ForeignKey("simulation_runs.id"), nullable=False, index=True)
    round_name = Column(String(50), nullable=False)
    position = Column(Integer, nullable=False)
    team_a_code = Column(String(3), nullable=True)
    team_b_code = Column(String(3), nullable=True)
    prob_a = Column(Float, nullable=True)
    prob_b = Column(Float, nullable=True)
