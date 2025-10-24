#!/usr/bin/env python3
"""
Create Admin User Script

This script creates an initial admin user from environment variables.
It's designed to be run during deployment to set up the first admin account.

Usage:
    python scripts/create_admin_user.py

Environment Variables:
    INITIAL_ADMIN_EMAIL: Email address for the admin user
    INITIAL_ADMIN_PASSWORD: Password for the admin user
    INITIAL_ADMIN_NAME: Full name for the admin user (optional)
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.database.connection import get_session
from app.services.auth_service import AuthService
from app.database.auth_models import UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_admin_user():
    """Create initial admin user from environment variables."""
    try:
        # Get admin credentials from environment
        admin_email = os.getenv("INITIAL_ADMIN_EMAIL")
        admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
        admin_name = os.getenv("INITIAL_ADMIN_NAME", "System Administrator")
        
        if not admin_email:
            logger.error("INITIAL_ADMIN_EMAIL environment variable is required")
            return False
        
        if not admin_password:
            logger.error("INITIAL_ADMIN_PASSWORD environment variable is required")
            return False
        
        # Validate email format
        if "@" not in admin_email:
            logger.error("INITIAL_ADMIN_EMAIL must be a valid email address")
            return False
        
        # Validate password strength
        if len(admin_password) < 8:
            logger.error("INITIAL_ADMIN_PASSWORD must be at least 8 characters long")
            return False
        
        # Get database session
        db = next(get_session())
        
        try:
            auth_service = AuthService(db)
            
            # Check if admin user already exists
            from app.repositories.user_repository import UserRepository
            user_repo = UserRepository(db)
            existing_user = user_repo.get_by_email(admin_email)
            
            if existing_user:
                if existing_user.role == UserRole.ADMIN:
                    logger.info(f"Admin user {admin_email} already exists with ADMIN role")
                    return True
                else:
                    logger.warning(f"User {admin_email} exists but is not an admin. Upgrading to admin...")
                    # Upgrade existing user to admin
                    user_repo.update_role(existing_user.id, UserRole.ADMIN)
                    logger.info(f"Upgraded user {admin_email} to ADMIN role")
                    return True
            
            # Create new admin user
            # Note: We need to create the first admin without requiring an existing admin
            # This is a special case for initial setup
            from app.core.security import hash_password
            
            user = user_repo.create_user(
                email=admin_email,
                password_hash=hash_password(admin_password),
                full_name=admin_name,
                role=UserRole.ADMIN,
                created_by_admin_id=None  # First admin has no creator
            )
            
            logger.info(f"Successfully created admin user: {admin_email}")
            logger.info(f"User ID: {user.id}")
            logger.info(f"Role: {user.role}")
            logger.info(f"Full Name: {user.full_name}")
            
            # Log the creation event
            from app.repositories.audit_log_repository import AuditLogRepository
            audit_repo = AuditLogRepository(db)
            audit_repo.create_log(
                user_id=None,  # System creation
                action="USER_CREATED",
                resource_type="user",
                resource_id=str(user.id),
                details={
                    "created_user_email": admin_email,
                    "role": "ADMIN",
                    "created_by": "system_script"
                }
            )
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        return False


def main():
    """Main function."""
    logger.info("Starting admin user creation script...")
    
    # Check if we're in the right directory
    if not (backend_dir / "app").exists():
        logger.error("This script must be run from the backend directory")
        sys.exit(1)
    
    # Check required environment variables
    required_vars = ["INITIAL_ADMIN_EMAIL", "INITIAL_ADMIN_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set the following environment variables:")
        logger.error("  INITIAL_ADMIN_EMAIL=your-email@domain.com")
        logger.error("  INITIAL_ADMIN_PASSWORD=your-secure-password")
        logger.error("  INITIAL_ADMIN_NAME='Your Full Name' (optional)")
        sys.exit(1)
    
    # Create admin user
    success = create_admin_user()
    
    if success:
        logger.info("Admin user creation completed successfully")
        sys.exit(0)
    else:
        logger.error("Admin user creation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
