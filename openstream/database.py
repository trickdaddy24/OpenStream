"""SQLite database engine and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from openstream.config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
    echo=settings.debug,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


def init_db():
    """Create all tables if they don't exist."""
    from openstream.models import Base

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session, closes on teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
