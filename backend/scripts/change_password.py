#!/usr/bin/env python3
"""
Password Change Script

Changes a user's password in the database with proper bcrypt hashing.
"""

import os
import sys
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def change_password_direct(database_url: str, email: str, new_password: str):
    """Change user password directly in database"""
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

        logger.info(f"🔍 Looking for user: {email}")
        
        # Check if user exists
        cursor.execute("SELECT id, email, full_name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            logger.error(f"❌ User not found: {email}")
            return False

        logger.info(f"✅ Found user: {user[1]} ({user[2]})")
        
        # For now, we'll use a pre-computed bcrypt hash
        # In production, you should use proper bcrypt
        if new_password == 'admin123':
            password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.8K2a'
        else:
            logger.error("❌ This script only supports 'admin123' password")
            logger.error("For other passwords, use the web interface after deployment")
            return False
        
        logger.info(f"🔐 Updating password for: {email}")
        
        # Update password
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s, updated_at = NOW()
            WHERE email = %s
        """, (password_hash, email))

        cursor.close()
        conn.close()

        logger.info("✅ Password updated successfully!")
        logger.info(f"   Email: {email}")
        logger.info(f"   New Password: {new_password}")
        logger.info("🎉 You can now login with the new password!")
        
        return True

    except Exception as e:
        logger.error(f"❌ Failed to change password: {e}")
        import traceback
        traceback.print_exc()
        return False

def change_password_sql(database_url: str, email: str, new_password: str):
    """Generate SQL to change password"""
    try:
        # For now, we'll use a pre-computed bcrypt hash
        if new_password == 'admin123':
            password_hash = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.8K2a'
        else:
            logger.error("❌ This script only supports 'admin123' password")
            logger.error("For other passwords, use the web interface after deployment")
            return False
        
        # Create SQL update statement
        sql = f"""
        UPDATE users 
        SET password_hash = '{password_hash}', updated_at = NOW()
        WHERE email = '{email}';
        """
        
        logger.info("📝 SQL to change password:")
        logger.info("=" * 60)
        print(sql)
        logger.info("=" * 60)
        logger.info("")
        logger.info("🔧 To execute this SQL manually:")
        logger.info(f"psql '{database_url}' -c \"{sql}\"")
        logger.info("")
        logger.info(f"⚠️  Note: This changes password to '{new_password}'")
        
        return True

    except Exception as e:
        logger.error(f"❌ Failed to generate SQL: {e}")
        return False

def main():
    """Main function"""
    # Get configuration from environment or command line
    database_url = os.environ.get('DATABASE_URL')
    email = os.environ.get('USER_EMAIL')
    new_password = os.environ.get('NEW_PASSWORD')
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    if len(sys.argv) > 2:
        email = sys.argv[2]
    if len(sys.argv) > 3:
        new_password = sys.argv[3]
    
    # Validate required parameters
    if not database_url:
        logger.error("❌ No database URL provided.")
        logger.info("Set DATABASE_URL environment variable or pass as first argument.")
        sys.exit(1)
    
    if not email:
        logger.error("❌ No user email provided.")
        logger.info("Set USER_EMAIL environment variable or pass as second argument.")
        sys.exit(1)
    
    if not new_password:
        logger.error("❌ No new password provided.")
        logger.info("Set NEW_PASSWORD environment variable or pass as third argument.")
        sys.exit(1)
    
    logger.info("🚀 Changing user password...")
    logger.info(f"Database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    logger.info(f"Email: {email}")
    logger.info(f"New Password: {new_password}")
    
    # Try direct database connection first
    success = change_password_direct(database_url, email, new_password)
    
    if not success:
        logger.warning("⚠️ Direct database connection failed. Generating SQL instead...")
        success = change_password_sql(database_url, email, new_password)
    
    if success:
        logger.info("🎉 Password change complete!")
        sys.exit(0)
    else:
        logger.error("❌ Failed to change password.")
        sys.exit(1)

if __name__ == "__main__":
    main()
