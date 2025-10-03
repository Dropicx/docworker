"""
Database connection and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

logger = logging.getLogger(__name__)

def get_database_url() -> str:
    """
    Get database URL from environment variables.
    Falls back to SQLite for local development if PostgreSQL not configured.
    """
    # Try PostgreSQL first (for Railway production)
    postgres_url = os.getenv("DATABASE_URL")
    if postgres_url:
        logger.info("Using PostgreSQL database from DATABASE_URL")
        return postgres_url
    
    # Try individual PostgreSQL components
    postgres_host = os.getenv("POSTGRES_HOST")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "doctranslator")
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    
    if postgres_host and postgres_password:
        postgres_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        logger.info("Using PostgreSQL database from individual components")
        return postgres_url
    
    # Fallback to SQLite for local development
    sqlite_url = "sqlite:///./doctranslator.db"
    logger.warning("No PostgreSQL configuration found, using SQLite for local development")
    return sqlite_url

def get_engine():
    """Get SQLAlchemy engine"""
    database_url = get_database_url()
    
    if database_url.startswith("sqlite"):
        # SQLite configuration
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False  # Set to True for SQL debugging
        )
    else:
        # PostgreSQL configuration
        engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=300
        )
    
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
