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
    
    # Check if token.json exists
    if not os.path.exists("token.json"):
        print("❌ Error: token.json not found!")
        print("Please run `python scripts/auth_google_drive.py` first to authenticate.")
        sys.exit(1)

    # The user requested to sync all documents to this specific organization for testing:
    test_workspace_id = UUID("32a1abfd-c59a-4d50-ac2c-e9da38c7de73")
    
    # Number of seconds to wait between syncs (e.g., 3600 = 1 hour)
    sync_interval_seconds = 60 * 5  # Default: 5 minutes
    
    print(f"Starting continuous sync for workspace_id: {test_workspace_id}")
    print(f"Sync interval set to {sync_interval_seconds} seconds.\n")
    
    while True:
        print(f"[{asyncio.get_event_loop().time()}] Triggering sync cycle...")
        try:
            await sync_drive_files(
                workspace_id=test_workspace_id,
                limit=10  # Process up to 10 files per cycle
            )
            print("✅ Sync cycle completed successfully.\n")
        except Exception as e:
            print(f"❌ Sync cycle failed: {e}\n")
            
        print(f"Waiting {sync_interval_seconds} seconds before next sync...\n")
        await asyncio.sleep(sync_interval_seconds)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Sync service stopped by user.")
