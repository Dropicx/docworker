#!/usr/bin/env python3
"""
Script to clear the processing cache
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio

from services.cleanup import emergency_cleanup, processing_store


async def clear_all_cache():
    """Clear all cached processing data"""
    print("🧹 Clearing all cached processing data...")

    # Clear the in-memory processing store
    if processing_store:
        count = len(processing_store)
        processing_store.clear()
        print(f"✅ Cleared {count} items from processing store")
    else:
        print("ℹ️ Processing store was already empty")

    # Run emergency cleanup for good measure
    await emergency_cleanup()

    print("✅ Cache cleared successfully!")


if __name__ == "__main__":
    asyncio.run(clear_all_cache())
