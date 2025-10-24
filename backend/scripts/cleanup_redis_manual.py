#!/usr/bin/env python3
"""
Manual Redis cleanup script for DocTranslator

Cleans up old Celery task results from Redis that weren't automatically cleaned
due to missing Celery Beat scheduler.

Usage:
    python3 scripts/cleanup_redis_manual.py

Features:
    - Sets TTL on keys without expiration
    - Deletes expired keys
    - Deletes old task results (>2 hours)
    - Shows before/after statistics
"""
import redis
import time
import json
from datetime import datetime
import sys

# Connect to Redis (dev database)
REDIS_URL = "redis://default:zXupOXcPiRwhKDNbTByOkGybUQpSHxDN@yamanote.proxy.rlwy.net:26905"

def format_bytes(bytes_val):
    """Format bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"

def main():
    print("=" * 80)
    print("REDIS CLEANUP - DOCTRANSLATOR DEV DATABASE")
    print("=" * 80)

    try:
        # Connect to Redis
        print(f"\n🔗 Connecting to Redis...")
        r = redis.from_url(REDIS_URL, decode_responses=False)
        r.ping()
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        sys.exit(1)

    # Get initial statistics
    print("\n" + "=" * 80)
    print("BEFORE CLEANUP")
    print("=" * 80)

    total_keys_before = r.dbsize()
    print(f"Total keys in database: {total_keys_before}")

    # Get memory info
    memory_info = r.info("memory")
    used_memory_before = memory_info.get('used_memory', 0)
    print(f"Memory used: {format_bytes(used_memory_before)}")

    # Get all celery result keys
    pattern = b'celery-task-meta-*'
    celery_keys = r.keys(pattern)
    print(f"\nCelery task result keys: {len(celery_keys)}")

    if not celery_keys:
        print("\n✅ No Celery result keys found - nothing to clean up!")
        return

    # Sample key TTLs
    ttl_samples = {}
    for key in celery_keys[:10]:
        ttl = r.ttl(key)
        if ttl == -1:
            ttl_samples[key.decode('utf-8', errors='ignore')] = "No expiration (PERMANENT)"
        elif ttl == -2:
            ttl_samples[key.decode('utf-8', errors='ignore')] = "Expired/Doesn't exist"
        else:
            ttl_samples[key.decode('utf-8', errors='ignore')] = f"{ttl}s ({ttl/3600:.2f}h)"

    print("\nSample key TTLs (first 10):")
    for key, ttl in ttl_samples.items():
        print(f"  {key[:60]}... → {ttl}")

    # Cleanup confirmation
    print("\n" + "=" * 80)
    print("CLEANUP ACTIONS")
    print("=" * 80)
    print("This script will:")
    print("  1. Set 1-hour TTL on keys without expiration")
    print("  2. Delete keys that are already expired")
    print("  3. Delete task results older than 2 hours")
    print()

    response = input("Proceed with cleanup? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Cleanup cancelled")
        return

    # Perform cleanup
    print("\n" + "=" * 80)
    print("CLEANING UP...")
    print("=" * 80)

    # Cleanup counters
    no_ttl_count = 0
    expired_count = 0
    old_count = 0
    error_count = 0

    current_time = time.time()

    for idx, key in enumerate(celery_keys):
        if idx % 100 == 0:
            print(f"Processing key {idx + 1}/{len(celery_keys)}...", end='\r')

        try:
            ttl = r.ttl(key)

            # Case 1: No expiration set (-1)
            if ttl == -1:
                # Set TTL to 1 hour instead of deleting
                r.expire(key, 3600)
                no_ttl_count += 1
                continue

            # Case 2: Already expired (-2)
            if ttl == -2:
                r.delete(key)
                expired_count += 1
                continue

            # Case 3: Check if result is older than 2 hours
            try:
                result_data = r.get(key)
                if result_data:
                    result_json = json.loads(result_data)
                    if 'date_done' in result_json:
                        try:
                            date_done = datetime.fromisoformat(result_json['date_done'].replace('Z', '+00:00'))
                            age_seconds = (datetime.now(date_done.tzinfo) - date_done).total_seconds()

                            # Delete results older than 2 hours
                            if age_seconds > 7200:
                                r.delete(key)
                                old_count += 1
                        except (ValueError, TypeError):
                            # Can't parse date, skip
                            pass
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Can't parse result, skip
                pass

        except Exception as e:
            error_count += 1
            if error_count < 5:  # Only show first 5 errors
                print(f"\n⚠️ Error processing key {key}: {e}")

    print()  # New line after progress

    # Get final statistics
    print("\n" + "=" * 80)
    print("CLEANUP RESULTS")
    print("=" * 80)

    print(f"\nKeys processed: {len(celery_keys)}")
    print(f"  - Keys with no TTL (set to 1h): {no_ttl_count}")
    print(f"  - Expired keys deleted: {expired_count}")
    print(f"  - Old (>2h) keys deleted: {old_count}")
    print(f"  - Errors encountered: {error_count}")

    total_cleaned = no_ttl_count + expired_count + old_count
    print(f"\n✅ Total keys cleaned: {total_cleaned}")

    # Final state
    print("\n" + "=" * 80)
    print("AFTER CLEANUP")
    print("=" * 80)

    total_keys_after = r.dbsize()
    remaining_celery_keys = len(r.keys(pattern))

    print(f"Total keys in database: {total_keys_after} (was {total_keys_before})")
    print(f"Keys removed: {total_keys_before - total_keys_after}")
    print(f"Remaining Celery keys: {remaining_celery_keys}")

    # Memory after cleanup
    memory_info = r.info("memory")
    used_memory_after = memory_info.get('used_memory', 0)
    memory_freed = used_memory_before - used_memory_after

    print(f"\nMemory used: {format_bytes(used_memory_after)} (was {format_bytes(used_memory_before)})")
    print(f"Memory freed: {format_bytes(memory_freed)}")

    # Recommendations
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n⚠️  This is a one-time cleanup. To prevent future accumulation:")
    print()
    print("1. Deploy Celery Beat service (automatic periodic cleanup)")
    print("   See: docs/REDIS_CLEANUP_ANALYSIS.md")
    print()
    print("2. Fix Redis TTL in backend client")
    print("   File: backend/app/services/celery_client.py")
    print()
    print("3. Monitor Redis memory usage regularly")
    print("   Command: redis-cli -u <redis-url> INFO memory")
    print()

if __name__ == '__main__':
    main()
