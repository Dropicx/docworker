#!/usr/bin/env python3
"""
Debug Celery Beat Service

Checks if beat service is working and why cleanup tasks might not be running.
"""

import redis
import json
from datetime import datetime

REDIS_URL = "redis://default:zXupOXcPiRwhKDNbTByOkGybUQpSHxDN@yamanote.proxy.rlwy.net:26905"


def main():
    print("=" * 80)
    print("CELERY BEAT SERVICE DIAGNOSTIC")
    print("=" * 80)

    r = redis.from_url(REDIS_URL, decode_responses=True)

    # 1. Check for beat schedule lock
    print("\n1. Checking Beat Scheduler Lock...")
    beat_keys = r.keys("celery-beat-*")
    if beat_keys:
        print(f"   ✅ Found {len(beat_keys)} beat-related keys (beat is running)")
        for key in beat_keys:
            print(f"      - {key}")
    else:
        print("   ❌ No beat-related keys found (beat might not be running)")

    # 2. Check for scheduled tasks in queues
    print("\n2. Checking Task Queues...")
    queues = ["high_priority", "default", "low_priority", "maintenance"]
    for queue in queues:
        length = r.llen(queue)
        if length > 0:
            print(f"   Queue '{queue}': {length} tasks pending")
            # Peek at first task
            task_raw = r.lindex(queue, 0)
            if task_raw:
                try:
                    task_data = json.loads(task_raw)
                    headers = task_data.get("headers", {})
                    task_name = headers.get("task", "Unknown")
                    print(f"      First task: {task_name}")
                except:
                    pass
        else:
            print(f"   Queue '{queue}': empty")

    # 3. Check for cleanup task results
    print("\n3. Checking Cleanup Task Execution History...")
    cleanup_tasks = [
        "cleanup_celery_results",
        "cleanup_orphaned_jobs",
        "cleanup_old_files",
        "database_maintenance",
    ]

    result_pattern = "celery-task-meta-*"
    result_keys = r.keys(result_pattern)

    cleanup_results_found = []
    for key in result_keys:
        try:
            result_data = r.get(key)
            if result_data:
                result = json.loads(result_data)
                task_name = result.get("task", "")
                if any(cleanup in task_name for cleanup in cleanup_tasks):
                    cleanup_results_found.append(
                        {
                            "key": key,
                            "task": task_name,
                            "status": result.get("status"),
                            "date_done": result.get("date_done"),
                        }
                    )
        except:
            pass

    if cleanup_results_found:
        print(f"   ✅ Found {len(cleanup_results_found)} cleanup task results:")
        for result in cleanup_results_found[-5:]:  # Last 5
            print(f"      - {result['task']}")
            print(f"        Status: {result['status']}")
            print(f"        Date: {result['date_done']}")
    else:
        print("   ❌ No cleanup task results found (tasks never ran)")

    # 4. Check beat schedule configuration
    print("\n4. Checking Beat Schedule Storage...")
    schedule_key = "celery-beat-schedule"
    if r.exists(schedule_key):
        print(f"   ✅ Beat schedule key exists")
        schedule_type = r.type(schedule_key)
        print(f"      Type: {schedule_type}")
        if schedule_type == "string":
            # Might be stored as JSON or pickle
            schedule_data = r.get(schedule_key)
            print(f"      Size: {len(schedule_data)} bytes")
    else:
        print("   ⚠️ No beat schedule key found")

    # 5. Check for worker registration
    print("\n5. Checking Worker Registration...")
    worker_keys = r.keys("celery-worker-*")
    if worker_keys:
        print(f"   ✅ Found {len(worker_keys)} registered workers")
        for key in worker_keys[:3]:  # Show first 3
            print(f"      - {key}")
    else:
        print("   ❌ No workers registered")

    # 6. Check for unacked tasks
    print("\n6. Checking Unacked Tasks (stuck tasks)...")
    unacked_keys = r.keys("unacked*")
    if unacked_keys:
        print(f"   ⚠️ Found {len(unacked_keys)} unacked task keys")
        for key in unacked_keys[:5]:
            print(f"      - {key}")
    else:
        print("   ✅ No unacked tasks")

    # 7. Memory and key count
    print("\n7. Redis Statistics...")
    info = r.info()
    print(f"   Total keys: {info.get('db0', {}).get('keys', 0)}")
    print(f"   Memory used: {info.get('used_memory_human', 'N/A')}")
    print(f"   Connected clients: {info.get('connected_clients', 0)}")

    # Diagnosis
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    if not beat_keys:
        print("\n❌ ISSUE: Beat service is NOT running")
        print("   - No beat-related keys in Redis")
        print("   - Check Railway logs for beat service")
        print("   - Command: railway logs --service doctranslator-beat")
        print()
        print("   Possible causes:")
        print("   1. Beat service failed to start (check logs)")
        print("   2. Beat service not deployed (check Railway dashboard)")
        print("   3. Beat service can't connect to Redis (check REDIS_URL)")

    elif not cleanup_results_found:
        print("\n⚠️ ISSUE: Beat is running but cleanup tasks never executed")
        print("   - Beat service appears to be running")
        print("   - But no cleanup task results found")
        print()
        print("   Possible causes:")
        print("   1. Tasks scheduled but worker not consuming maintenance queue")
        print("   2. Tasks failing silently (check worker logs)")
        print("   3. Schedule not properly loaded (check beat logs)")
        print("   4. Tasks going to wrong queue")

    elif r.llen("maintenance") > 0:
        print("\n⚠️ ISSUE: Tasks queued but not being processed")
        print(f"   - {r.llen('maintenance')} tasks stuck in maintenance queue")
        print()
        print("   Possible causes:")
        print("   1. Worker not consuming maintenance queue")
        print("   2. Worker crashed (check worker logs)")
        print("   3. Worker at max capacity")

    else:
        print("\n✅ Beat service appears to be working")
        print("   - Beat keys found in Redis")
        print("   - Cleanup task results exist")
        print()
        print("   If Redis still has old keys, the issue might be:")
        print("   1. Cleanup tasks not removing all old keys (check task logic)")
        print("   2. New keys being created faster than cleanup")
        print("   3. Cleanup schedule too infrequent")

    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Check Railway logs:")
    print("   gh api repos/OWNER/REPO/actions/runs --jq '.workflow_runs[0].logs_url'")
    print("   Or: Railway dashboard → beat service → Logs")
    print()
    print("2. Check beat service status:")
    print("   Railway dashboard → Services → doctranslator-beat")
    print()
    print("3. Check worker logs:")
    print("   Railway dashboard → Services → doctranslator-worker → Logs")
    print("   Look for: 'Received task: cleanup_celery_results'")
    print()
    print("4. Manual task trigger (test if worker can process cleanup):")
    print("   See: backend/scripts/trigger_cleanup_manual.py")


if __name__ == "__main__":
    main()
