#!/usr/bin/env python3
"""Quick check of what's actually in Redis"""
import redis

REDIS_URL = "redis://default:zXupOXcPiRwhKDNbTByOkGybUQpSHxDN@yamanote.proxy.rlwy.net:26905"
r = redis.from_url(REDIS_URL, decode_responses=True)

print("All keys in Redis:")
all_keys = r.keys("*")
for key in sorted(all_keys):
    key_type = r.type(key)
    ttl = r.ttl(key)
    ttl_str = f"{ttl}s" if ttl >= 0 else ("No expiration" if ttl == -1 else "Expired")
    print(f"  {key} ({key_type}) - TTL: {ttl_str}")

print(f"\nTotal: {len(all_keys)} keys")
