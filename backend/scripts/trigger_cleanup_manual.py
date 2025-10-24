#!/usr/bin/env python3
"""
Manually trigger cleanup tasks

Tests if cleanup tasks work when manually invoked (bypassing beat scheduler).
This helps identify if the issue is with beat scheduling or with the tasks themselves.
"""
import sys
import os

# Add paths
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/worker')
sys.path.insert(0, '/app/shared')

from celery import Celery

# Connect to Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://default:zXupOXcPiRwhKDNbTByOkGybUQpSHxDN@yamanote.proxy.rlwy.net:26905')

# Create Celery client
celery_client = Celery('doctranslator_backend', broker=REDIS_URL, backend=REDIS_URL)
celery_client.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)

def trigger_task(task_name, description):
    """Trigger a cleanup task and wait for result"""
    print(f"\n{'=' * 80}")
    print(f"Triggering: {description}")
    print(f"Task: {task_name}")
    print(f"{'=' * 80}")

    try:
        # Send task to maintenance queue
        result = celery_client.send_task(
            task_name,
            queue='maintenance'
        )

        print(f"✅ Task queued with ID: {result.id}")
        print(f"Waiting for result (timeout: 60s)...")

        # Wait for result with timeout
        task_result = result.get(timeout=60)

        print(f"\n✅ Task completed successfully!")
        print(f"Result: {task_result}")

        return True

    except Exception as e:
        print(f"\n❌ Task failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

def main():
    print("=" * 80)
    print("MANUAL CLEANUP TASK TRIGGER")
    print("=" * 80)
    print()
    print("This script manually triggers cleanup tasks to test if they work.")
    print("If tasks succeed here but don't run automatically, the issue is with Beat.")
    print()

    tasks = [
        ('cleanup_celery_results', 'Clean up old Celery task results from Redis'),
        ('cleanup_orphaned_jobs', 'Clean up orphaned pipeline jobs'),
        ('cleanup_old_files', 'Clean up old temporary files'),
        ('database_maintenance', 'Database maintenance and cleanup'),
    ]

    print(f"Connected to Redis: {REDIS_URL.split('@')[0]}...")
    print()

    # Show available tasks
    print("Available cleanup tasks:")
    for i, (task_name, description) in enumerate(tasks, 1):
        print(f"  {i}. {task_name}")
        print(f"     {description}")
    print()

    # Ask which task to run
    print("Enter task number to run (or 'all' to run all tasks):")
    choice = input("> ").strip().lower()

    results = {}

    if choice == 'all':
        print("\nRunning all cleanup tasks...")
        for task_name, description in tasks:
            success = trigger_task(task_name, description)
            results[task_name] = success
    elif choice.isdigit() and 1 <= int(choice) <= len(tasks):
        idx = int(choice) - 1
        task_name, description = tasks[idx]
        success = trigger_task(task_name, description)
        results[task_name] = success
    else:
        print("❌ Invalid choice")
        return

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for task_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {task_name}")

    # Analysis
    if all(results.values()):
        print("\n✅ All tasks completed successfully!")
        print()
        print("DIAGNOSIS:")
        print("  - Cleanup tasks work correctly when manually triggered")
        print("  - Issue is likely with Beat scheduler not running or not scheduling")
        print()
        print("NEXT STEPS:")
        print("  1. Check if beat service is running on Railway")
        print("  2. Check beat service logs for errors")
        print("  3. Verify CELERYBEAT_SCHEDULE in worker/config.py")
    elif any(results.values()):
        print("\n⚠️ Some tasks succeeded, some failed")
        print()
        print("DIAGNOSIS:")
        print("  - Worker is running and can process some tasks")
        print("  - Failed tasks have implementation issues")
        print()
        print("NEXT STEPS:")
        print("  1. Check worker logs for error details")
        print("  2. Review implementation of failed tasks")
    else:
        print("\n❌ All tasks failed")
        print()
        print("DIAGNOSIS:")
        print("  - Worker might not be running")
        print("  - Worker can't connect to Redis")
        print("  - Tasks not properly registered")
        print()
        print("NEXT STEPS:")
        print("  1. Check if worker service is running")
        print("  2. Check worker logs for errors")
        print("  3. Verify REDIS_URL configuration")

if __name__ == '__main__':
    main()
