#!/usr/bin/env python3
"""
Test Script for Google Drive Sync Pipeline.
This script triggers the background sync manually for testing purposes.
"""

import os
import sys
import asyncio
from uuid import uuid4, UUID

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipelines.ingestion.sync_drive import sync_drive_files

async def main():
    print("="*50)
    print("🚀 Google Drive Continuous Sync Service")
    print("="*50)
    
    # The sync interval (e.g., 3600 = 1 hour)
    sync_interval_seconds = 60 * 5  # Default: 5 minutes
    
    print(f"Starting continuous sync for all active organizations")
    print(f"Sync interval set to {sync_interval_seconds} seconds.\n")
    
    while True:
        print(f"[{asyncio.get_event_loop().time()}] Triggering sync cycle...")
        try:
            processed_count = await sync_drive_files(
                limit=10  # Process up to 10 files per cycle
            )
            if processed_count == 0:
                print("⚠️ No active Google Drive connectors found. Make sure it's enabled in the UI.\n")
            else:
                print(f"✅ Sync cycle completed successfully. Processed {processed_count} organizations.\n")
        except Exception as e:
            print(f"❌ Sync cycle failed: {e}\n")
            
        print(f"Waiting {sync_interval_seconds} seconds before next sync...\n")
        await asyncio.sleep(sync_interval_seconds)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Sync service stopped by user.")
