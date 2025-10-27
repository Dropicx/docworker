#!/usr/bin/env python3
"""
API Key Management CLI

This CLI tool provides commands for managing API keys including creation,
listing, revocation, and cleanup operations.

Usage:
    python scripts/manage_api_keys.py <command> [options]

Commands:
    create <user_email> <name> [--expires-days DAYS]  Create API key for user
    list <user_email>                                 List user's API keys
    list-all                                          List all API keys (admin)
    revoke <key_id>                                   Revoke API key
    cleanup                                           Clean up expired keys
    stats                                             Show API key statistics
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.connection import get_session
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.repositories.api_key_repository import APIKeyRepository


def create_api_key(user_email, name, expires_days=None):
    """Create an API key for a user."""
    db = next(get_session())
    try:
        # Get user
        user_repo = UserRepository(db)
        user = user_repo.get_by_email(user_email)
        if not user:
            print(f"Error: User {user_email} not found")
            return False
        
        # Create API key
        auth_service = AuthService(db)
        plain_key, key_id = auth_service.create_api_key(
            user_id=user.id,
            name=name,
            expires_days=expires_days
        )
        
        print(f"Created API key for user {user_email}")
        print(f"Key ID: {key_id}")
        print(f"Name: {name}")
        print(f"API Key: {plain_key}")
        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
            print(f"Expires: {expires_at.isoformat()}")
        else:
            print("Expires: Never")
        print()
        print("IMPORTANT: Save this API key now! It will not be shown again.")
        
        return True
        
    except Exception as e:
        print(f"Error creating API key: {e}")
        return False
    finally:
        db.close()


def list_user_keys(user_email):
    """List API keys for a user."""
    db = next(get_session())
    try:
        # Get user
        user_repo = UserRepository(db)
        user = user_repo.get_by_email(user_email)
        if not user:
            print(f"Error: User {user_email} not found")
            return False
        
        # Get API keys
        api_key_repo = APIKeyRepository(db)
        keys = api_key_repo.get_by_user(user.id)
        
        if not keys:
            print(f"No API keys found for user {user_email}")
            return True
        
        print(f"API Keys for user {user_email}:")
        print("-" * 60)
        print(f"{'ID':<36} {'Name':<20} {'Active':<8} {'Expires':<20} {'Last Used':<20}")
        print("-" * 60)
        
        for key in keys:
            expires_str = key.expires_at.isoformat() if key.expires_at else "Never"
            last_used_str = key.last_used_at.isoformat() if key.last_used_at else "Never"
            print(f"{key.id} {key.name:<20} {key.is_active!s:<8} {expires_str:<20} {last_used_str:<20}")
        
        return True
        
    except Exception as e:
        print(f"Error listing API keys: {e}")
        return False
    finally:
        db.close()


def list_all_keys():
    """List all API keys (admin only)."""
    db = next(get_session())
    try:
        api_key_repo = APIKeyRepository(db)
        keys = api_key_repo.get_all_active()
        
        if not keys:
            print("No API keys found")
            return True
        
        print("All API Keys:")
        print("-" * 80)
        print(f"{'ID':<36} {'User':<30} {'Name':<15} {'Active':<8} {'Expires':<20}")
        print("-" * 80)
        
        for key in keys:
            expires_str = key.expires_at.isoformat() if key.expires_at else "Never"
            print(f"{key.id} {key.user.email:<30} {key.name:<15} {key.is_active!s:<8} {expires_str:<20}")
        
        return True
        
    except Exception as e:
        print(f"Error listing all API keys: {e}")
        return False
    finally:
        db.close()


def revoke_key(key_id):
    """Revoke an API key."""
    db = next(get_session())
    try:
        api_key_repo = APIKeyRepository(db)
        
        # Get key
        key = api_key_repo.get_by_id(key_id)
        if not key:
            print(f"Error: API key {key_id} not found")
            return False
        
        # Revoke key
        success = api_key_repo.revoke_key(key_id)
        if not success:
            print(f"Error: Failed to revoke API key {key_id}")
            return False
        
        print(f"Successfully revoked API key {key_id}")
        print(f"Key name: {key.name}")
        print(f"User: {key.user.email}")
        
        return True
        
    except Exception as e:
        print(f"Error revoking API key: {e}")
        return False
    finally:
        db.close()


def cleanup_expired_keys():
    """Clean up expired API keys."""
    db = next(get_session())
    try:
        api_key_repo = APIKeyRepository(db)
        
        # Get expired keys
        expired_keys = api_key_repo.get_expired_keys()
        if not expired_keys:
            print("No expired API keys found")
            return True
        
        print(f"Found {len(expired_keys)} expired API keys:")
        for key in expired_keys:
            print(f"  - {key.id} ({key.name}) - User: {key.user.email}")
        
        # Clean up
        count = api_key_repo.cleanup_expired_keys()
        print(f"Cleaned up {count} expired API keys")
        
        return True
        
    except Exception as e:
        print(f"Error cleaning up expired keys: {e}")
        return False
    finally:
        db.close()


def show_stats():
    """Show API key statistics."""
    db = next(get_session())
    try:
        api_key_repo = APIKeyRepository(db)
        user_repo = UserRepository(db)
        
        # Get statistics
        total_keys = api_key_repo.count()
        active_keys = len(api_key_repo.get_all_active())
        expired_keys = len(api_key_repo.get_expired_keys())
        total_users = user_repo.count()
        
        print("API Key Statistics:")
        print("-" * 30)
        print(f"Total API keys: {total_keys}")
        print(f"Active keys: {active_keys}")
        print(f"Expired keys: {expired_keys}")
        print(f"Total users: {total_users}")
        
        # Recent activity
        recent_keys = []
        for user in user_repo.get_active_users():
            user_keys = api_key_repo.get_recently_used(user.id, days=7)
            recent_keys.extend(user_keys)
        
        if recent_keys:
            print(f"Recently used keys (7 days): {len(recent_keys)}")
        
        return True
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
        return False
    finally:
        db.close()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Manage DocTranslator API keys"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create API key for user")
    create_parser.add_argument("user_email", help="User email address")
    create_parser.add_argument("name", help="API key name")
    create_parser.add_argument("--expires-days", type=int, help="Days until expiration")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List user's API keys")
    list_parser.add_argument("user_email", help="User email address")
    
    # List all command
    subparsers.add_parser("list-all", help="List all API keys (admin)")
    
    # Revoke command
    revoke_parser = subparsers.add_parser("revoke", help="Revoke API key")
    revoke_parser.add_argument("key_id", help="API key ID to revoke")
    
    # Cleanup command
    subparsers.add_parser("cleanup", help="Clean up expired keys")
    
    # Stats command
    subparsers.add_parser("stats", help="Show API key statistics")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    print("DocTranslator API Key Manager")
    print("=" * 40)
    print()
    
    success = False
    
    if args.command == "create":
        success = create_api_key(args.user_email, args.name, args.expires_days)
    elif args.command == "list":
        success = list_user_keys(args.user_email)
    elif args.command == "list-all":
        success = list_all_keys()
    elif args.command == "revoke":
        success = revoke_key(args.key_id)
    elif args.command == "cleanup":
        success = cleanup_expired_keys()
    elif args.command == "stats":
        success = show_stats()
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
