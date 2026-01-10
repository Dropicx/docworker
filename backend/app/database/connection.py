"""
Database connection and session management using centralized configuration.
"""

from collections.abc import Generator
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_engine():
    """
    Get SQLAlchemy engine with configuration from settings.

    PostgreSQL is required for production. Configuration is validated on startup.
    """
    database_url = settings.database_url

    # PostgreSQL configuration
    engine = create_engine(
        database_url,
        echo=settings.debug,  # SQL query logging in debug mode
        pool_pre_ping=True,  # Verify connections before using
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=300,  # Recycle connections after 5 minutes
    )

    logger.info(f"Database engine created with pool_size={settings.db_pool_size}")

    return engine


def get_session() -> Generator[Session, None, None]:
    """Get database session"""
    engine = get_engine()
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session as a generator.

    Usage (with next):
        db = next(get_db_session())
        try:
            repo = SomeRepository(db)
            ...
        finally:
            db.close()

    This is an alias for get_session() for backward compatibility.
    """
    return get_session()


@contextmanager
def get_db_session_context():
    """
    Get database session as a context manager for use in non-FastAPI contexts.

    Usage:
        with get_db_session_context() as db:
            repo = SomeRepository(db)
            ...

    This is the preferred way to get a session in Celery tasks and scripts.
    """
    engine = get_engine()
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


# Global engine instance
engine = get_engine()
