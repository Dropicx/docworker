#!/usr/bin/env python3
"""
Inspect Redis database for task cleanup issues
"""
import redis
from datetime import datetime, timedelta
import json

# Connect to Redis
redis_url = "redis://default:zXupOXcPiRwhKDNbTByOkGybUQpSHxDN@yamanote.proxy.rlwy.net:26905"
r = redis.from_url(redis_url, decode_responses=True)

print("=" * 80)
print("REDIS DATABASE INSPECTION")
print("=" * 80)

# Get all keys
keys = r.keys("*")
print(f"\nTotal keys in database: {len(keys)}")

# Group keys by pattern
key_patterns = {}
for key in keys:
    # Extract pattern (prefix before UUID/ID)
    parts = key.split(":")
    if len(parts) > 1:
        pattern = ":".join(parts[:-1]) if parts[-1].replace("-", "").isalnum() and len(parts[-1]) > 10 else key
    else:
        pattern = key

    if pattern not in key_patterns:
        key_patterns[pattern] = []
    key_patterns[pattern].append(key)

print("\n" + "=" * 80)
print("KEY PATTERNS AND COUNTS")
print("=" * 80)
for pattern, pattern_keys in sorted(key_patterns.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n{pattern}")
    print(f"  Count: {len(pattern_keys)}")

    # Check TTL for first key
    if pattern_keys:
        ttl = r.ttl(pattern_keys[0])
        if ttl == -1:
            print(f"  TTL: No expiration set (PERMANENT)")
        elif ttl == -2:
            print(f"  TTL: Key doesn't exist or expired")
        else:
            print(f"  TTL: {ttl} seconds ({ttl/3600:.2f} hours)")

# Celery-specific inspection
print("\n" + "=" * 80)
print("CELERY TASK ANALYSIS")
print("=" * 80)

celery_keys = [k for k in keys if "celery" in k.lower() or "task" in k.lower()]
print(f"\nCelery-related keys: {len(celery_keys)}")

# Check for task results
result_keys = [k for k in keys if "result" in k.lower()]
print(f"Task result keys: {len(result_keys)}")

if result_keys:
    print("\nSample task results (first 5):")
    for key in result_keys[:5]:
        ttl = r.ttl(key)
        key_type = r.type(key)
        print(f"\n  Key: {key}")
        print(f"  Type: {key_type}")
        print(f"  TTL: {ttl if ttl >= 0 else 'No expiration' if ttl == -1 else 'Expired'}")

        # Try to get value
        try:
            if key_type == "string":
                value = r.get(key)
                if value and len(value) < 500:
                    print(f"  Value: {value[:200]}...")
        except Exception as e:
            print(f"  Error reading value: {e}")

# Check for pending tasks
print("\n" + "=" * 80)
print("PENDING/QUEUED TASKS")
print("=" * 80)

# Check default Celery queues
queues = ["celery", "default", "document_processing"]
for queue in queues:
    length = r.llen(queue)
    if length > 0:
        print(f"\nQueue '{queue}': {length} tasks")

# Check for unacked tasks
unacked_keys = [k for k in keys if "unacked" in k.lower()]
if unacked_keys:
    print(f"\nUnacknowledged task keys: {len(unacked_keys)}")
    for key in unacked_keys[:5]:
        print(f"  - {key}")

# Memory usage
info = r.info("memory")
print("\n" + "=" * 80)
print("MEMORY USAGE")
print("=" * 80)
print(f"Used memory: {info.get('used_memory_human', 'N/A')}")
print(f"Peak memory: {info.get('used_memory_peak_human', 'N/A')}")
print(f"Total keys: {r.dbsize()}")

# Recommendations
print("\n" + "=" * 80)
print("CLEANUP RECOMMENDATIONS")
print("=" * 80)

permanent_keys = []
for key in keys:
    if r.ttl(key) == -1:
        permanent_keys.append(key)

if permanent_keys:
    print(f"\n⚠️  Found {len(permanent_keys)} keys without expiration (permanent)")
    print("\nSample permanent keys:")
    for key in permanent_keys[:10]:
        print(f"  - {key}")

    print("\n🔧 SOLUTION: Set TTL on task results")
    print("   Celery should be configured with result_expires setting")

if len(keys) > 1000:
    print(f"\n⚠️  Large number of keys ({len(keys)}) - consider cleanup")
    print("   - Enable Celery result expiration")
    print("   - Use result_backend_transport_options with TTL")
    print("   - Implement periodic cleanup task")

print("\n" + "=" * 80)
