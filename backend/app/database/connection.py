"""
Database connection and session management using centralized configuration.
"""

from collections.abc import Generator
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
        pool_recycle=300  # Recycle connections after 5 minutes
    )

    logger.info(f"Database engine created with pool_size={settings.db_pool_size}")

    return engine

def get_session() -> Generator[Session, None, None]:
    """Get database session"""
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session (alias for get_session for compatibility).
    Returns a generator that yields a SQLAlchemy Session.
    """
    return get_session()

# Global engine instance
engine = get_engine()
