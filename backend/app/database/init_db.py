"""
Database initialization script
"""

import logging
from sqlalchemy import create_engine
from app.database.models import Base
from app.database.connection import get_database_url

logger = logging.getLogger(__name__)

def init_database():
    """Initialize database tables and seed initial data"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Seed initial data
        try:
            from app.database.simple_seed import simple_seed_database
            if simple_seed_database():
                logger.info("Database seeded with initial data successfully")
            else:
                logger.warning("Failed to seed database with initial data")
        except Exception as e:
            logger.error(f"Error during database seeding: {e}")
            logger.warning("Continuing without seeding - database tables created but empty")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def drop_database():
    """Drop all database tables (use with caution!)"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
        
        return True
    except Exception as e:
        logger.error(f"Failed to drop database: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        print("Dropping database tables...")
        success = drop_database()
        print("✅ Database dropped" if success else "❌ Failed to drop database")
    else:
        print("Initializing database...")
        success = init_database()
        print("✅ Database initialized" if success else "❌ Failed to initialize database")
