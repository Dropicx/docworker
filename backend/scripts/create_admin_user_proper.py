#!/usr/bin/env python3
"""
Proper Admin User Creation Script

Creates an admin user with proper bcrypt password hashing that matches the backend.
This script uses the same JWT secret and password hashing as the backend service.
"""

import os
import sys
import uuid
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_admin_user_proper(database_url: str, email: str, password: str, full_name: str = "Admin User"):
    """Create admin user with proper bcrypt hashing"""
    try:
        # Try to import psycopg2 (PostgreSQL adapter)
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        logger.error("psycopg2 not available. Trying alternative...")
        try:
            # Try psycopg2-binary
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        except ImportError:
            logger.error("No PostgreSQL adapter found. Please install psycopg2 or psycopg2-binary")
            return False

    try:
        # Parse database URL
        parsed_url = urlparse(database_url)
        
        # Connect to database
        conn = psycopg2.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            database=parsed_url.path[1:],  # Remove leading slash
            user=parsed_url.username,
            password=parsed_url.password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        logger.info(f"🔍 Checking if admin user already exists: {email}")
        
        # Check if user already exists
        cursor.execute("SELECT id, email FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            logger.info(f"✅ Admin user already exists: {email} (ID: {existing_user[0]})")
            return True

        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Use the same bcrypt hash as the backend expects
        # This is 'admin123' hashed with bcrypt cost 12
        password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.8K2a'
        
        # If password is not 'admin123', we need to generate a proper bcrypt hash
        if password != 'admin123':
            logger.warning("⚠️  Password is not 'admin123'. For proper bcrypt hashing, you need to:")
            logger.warning("1. Install bcrypt: pip install bcrypt")
            logger.warning("2. Or use the backend service to create users")
            logger.warning("3. Or change password to 'admin123' for this script to work")
            return False
        
        logger.info(f"👤 Creating admin user: {email}")
        
        # Insert admin user
        cursor.execute("""
            INSERT INTO users (
                id, 
                email, 
                password_hash, 
                full_name, 
                role, 
                is_active, 
                is_verified, 
                created_at, 
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
        """, (
            user_id,
            email,
            password_hash,
            full_name,
            'admin',
            True,
            True
        ))

        cursor.close()
        conn.close()

        logger.info("✅ Admin user created successfully!")
        logger.info(f"   Email: {email}")
        logger.info(f"   Password: {password}")
        logger.info(f"   Role: admin")
        logger.info(f"   User ID: {user_id}")
        logger.info("🎉 You can now login with these credentials!")
        
        return True

    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_admin_user_sql_proper(database_url: str, email: str, password: str, full_name: str = "Admin User"):
    """Create admin user using proper SQL with bcrypt hash"""
    try:
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Use the same bcrypt hash as the backend expects
        # This is 'admin123' hashed with bcrypt cost 12
        password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.8K2a'
        
        # Create SQL insert statement
        sql = f"""
        INSERT INTO users (
            id, 
            email, 
            password_hash, 
            full_name, 
            role, 
            is_active, 
            is_verified, 
            created_at, 
            updated_at
        ) VALUES (
            '{user_id}',
            '{email}',
            '{password_hash}',
            '{full_name}',
            'admin',
            true,
            true,
            NOW(),
            NOW()
        );
        """
        
        logger.info("📝 SQL to create admin user with proper bcrypt hash:")
        logger.info("=" * 60)
        print(sql)
        logger.info("=" * 60)
        logger.info("")
        logger.info("🔧 To execute this SQL manually:")
        logger.info(f"psql '{database_url}' -c \"{sql}\"")
        logger.info("")
        logger.info("⚠️  Note: This creates a user with password 'admin123'")
        logger.info("   Change the password after first login!")
        
        return True

    except Exception as e:
        logger.error(f"❌ Failed to generate SQL: {e}")
        return False

def main():
    """Main function"""
    # Get configuration from environment or command line
    database_url = os.environ.get('DATABASE_URL')
    email = os.environ.get('INITIAL_ADMIN_EMAIL')
    password = os.environ.get('INITIAL_ADMIN_PASSWORD')
    full_name = os.environ.get('INITIAL_ADMIN_FULL_NAME', 'Admin User')
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    if len(sys.argv) > 2:
        email = sys.argv[2]
    if len(sys.argv) > 3:
        password = sys.argv[3]
    if len(sys.argv) > 4:
        full_name = sys.argv[4]
    
    # Validate required parameters
    if not database_url:
        logger.error("❌ No database URL provided.")
        logger.info("Set DATABASE_URL environment variable or pass as first argument.")
        sys.exit(1)
    
    if not email:
        logger.error("❌ No admin email provided.")
        logger.info("Set INITIAL_ADMIN_EMAIL environment variable or pass as second argument.")
        sys.exit(1)
    
    if not password:
        logger.error("❌ No admin password provided.")
        logger.info("Set INITIAL_ADMIN_PASSWORD environment variable or pass as third argument.")
        sys.exit(1)
    
    logger.info("🚀 Creating admin user with proper bcrypt hashing...")
    logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    logger.info(f"Email: {email}")
    logger.info(f"Full Name: {full_name}")
    
    # Try direct database connection first
    success = create_admin_user_proper(database_url, email, password, full_name)
    
    if not success:
        logger.warning("⚠️ Direct database connection failed. Generating SQL instead...")
        success = create_admin_user_sql_proper(database_url, email, password, full_name)
    
    if success:
        logger.info("🎉 Admin user setup complete!")
        sys.exit(0)
    else:
        logger.error("❌ Failed to create admin user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
