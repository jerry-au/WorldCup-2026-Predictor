from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

_engine_kwargs = dict(
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)
if "mysql" in settings.database_url:
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=3600)

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
