"""Simulation preset model for tournament simulation parameters."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from ..database import Base


class SimulationPreset(Base):
    __tablename__ = "simulation_presets"

    id = Column(String(36), primary_key=True)
    name = Column(String(80), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_builtin = Column(Boolean, nullable=False, default=False)
    parameters_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
