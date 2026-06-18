"""Data refresh status tracking model."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text, Float

from ..database import Base


class DataRefreshLog(Base):
    __tablename__ = "data_refresh_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    refresh_type = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False)  # running / success / failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    records_updated = Column(Integer, default=0)
    progress = Column(Float, default=0.0)  # 0.0 ~ 100.0
    error_message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)

    @staticmethod
    def log_start(source: str, refresh_type: str) -> "DataRefreshLog":
        return DataRefreshLog(
            source=source,
            refresh_type=refresh_type,
            status="running",
            started_at=datetime.utcnow(),
            progress=0.0,
        )

    def update_progress(self, value: float, total: float | None = None):
        """Update progress. If total provided, calculate percentage."""
        if total and total > 0:
            self.progress = min(round(value / total * 100, 1), 100.0)
        else:
            self.progress = min(value, 100.0)

    def mark_complete(self, records_updated: int = 0, details: str = None):
        self.status = "success"
        self.completed_at = datetime.utcnow()
        self.records_updated = records_updated
        self.details = details
        self.progress = 100.0

    def mark_failed(self, error_message: str):
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message


class DataSourceStatus(Base):
    __tablename__ = "data_source_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, unique=True)
    last_refresh = Column(DateTime, nullable=True)
    next_scheduled = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)
    refresh_interval_hours = Column(Integer, default=8)
    match_day_interval_hours = Column(Integer, default=4)
    notes = Column(Text, nullable=True)

    def needs_refresh(self, is_match_day: bool = False) -> bool:
        if not self.last_refresh:
            return True

        interval = self.match_day_interval_hours if is_match_day else self.refresh_interval_hours
        elapsed = (datetime.utcnow() - self.last_refresh).total_seconds() / 3600
        return elapsed >= interval
