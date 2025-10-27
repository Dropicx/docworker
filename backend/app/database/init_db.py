"""
Database initialization script
"""

import logging

from sqlalchemy import create_engine

from app.core.config import settings

# Import modular pipeline models to register them with Base.metadata
from app.database.unified_models import Base

logger = logging.getLogger(__name__)


def init_database():
    """Initialize database tables and seed initial data"""
    try:
        engine = create_engine(settings.database_url)

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Seed modular pipeline configuration
        try:
            from app.database.modular_pipeline_seed import seed_modular_pipeline

            if seed_modular_pipeline():
                logger.info("Database seeded with modular pipeline configuration successfully")
            else:
                logger.warning("Failed to seed modular pipeline configuration")
        except Exception as e:
            logger.error(f"Error during modular pipeline seeding: {e}")
            logger.warning(
                "Continuing without modular pipeline seeding - modular pipeline tables may be empty"
            )

        # Create initial admin user if environment variables are set
        try:
            from app.database.connection import get_session
            from app.services.auth_service import AuthService
            from app.repositories.user_repository import UserRepository
            from app.database.auth_models import UserRole
            import os

            admin_email = os.getenv("INITIAL_ADMIN_EMAIL")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
            admin_name = os.getenv("INITIAL_ADMIN_NAME", "System Administrator")

            if admin_email and admin_password:
                db = next(get_session())
                try:
                    user_repo = UserRepository(db)
                    existing_user = user_repo.get_by_email(admin_email)

                    if existing_user:
                        if existing_user.role == UserRole.ADMIN:
                            logger.info(f"✅ Admin user {admin_email} already exists")
                        else:
                            # User exists but not admin, make them admin
                            existing_user.role = UserRole.ADMIN
                            db.commit()
                            logger.info(f"✅ Updated existing user {admin_email} to ADMIN role")
                    else:
                        # Create new admin user
                        auth_service = AuthService(db)
                        result = auth_service.register_user(
                            email=admin_email,
                            password=admin_password,
                            full_name=admin_name,
                            role=UserRole.ADMIN
                        )
                        if result:
                            logger.info(f"✅ Created new admin user: {admin_email}")
                        else:
                            logger.warning(f"❌ Failed to create admin user")
                except Exception as e:
                    logger.error(f"Error creating admin user: {e}")
                finally:
                    db.close()
            else:
                logger.info("ℹ️ INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD not set - skipping admin user creation")
        except Exception as e:
            logger.error(f"Error during admin user creation: {e}")
            logger.warning("Continuing without admin user creation - manual creation may be required")

        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def drop_database():
    """Drop all database tables (use with caution!)"""
    try:
        engine = create_engine(settings.database_url)

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
