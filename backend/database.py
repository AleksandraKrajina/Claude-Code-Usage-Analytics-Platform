"""Database connection and session management."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# SQLite needs check_same_thread=False for FastAPI; PostgreSQL uses pool
_db_url = settings.database_url
_connect_args = {}
if _db_url.startswith("sqlite"):
    Path("./data").mkdir(exist_ok=True)
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    pool_pre_ping=not _db_url.startswith("sqlite"),
    pool_size=10 if not _db_url.startswith("sqlite") else 5,
    max_overflow=20 if not _db_url.startswith("sqlite") else 0,
    echo=settings.debug,
)

IS_SQLITE = engine.dialect.name == "sqlite"

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Provide a transactional scope for database operations.
    
    Yields:
        Session: SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables.
    Creates all tables defined in models.
    """
    from backend.models import TelemetryEvent, Employee  # noqa: F401
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")
