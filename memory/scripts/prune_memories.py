#!/usr/bin/env python3
"""
Memory Pruning Script
Intelligently cleanup old, low-value memories
Keeps high-value memories, removes clutter
"""

import sys
import urllib.request
import urllib.error
import json
from datetime import datetime, timedelta
from typing import List, Dict

MEMORY_API = "http://localhost:8100"

class MemoryPruner:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.deleted_count = 0
        self.kept_count = 0
        self.bytes_freed = 0

    def log(self, message: str):
        print(message)

    def api_request(self, endpoint: str, method='GET', data=None):
        """Make API request"""
        url = f"{MEMORY_API}{endpoint}"
        headers = {'Content-Type': 'application/json'}

        try:
            if data:
                req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'),
                                            headers=headers, method=method)
            else:
                req = urllib.request.Request(url, headers=headers, method=method)

            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.log(f"API Error: {e}")
            return None

    def should_delete(self, memory: Dict, cutoff_date: datetime) -> bool:
        """Determine if memory should be deleted"""
        # Parse created date
        try:
            created_at = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
        except:
            return False

        # Keep if recent (newer than cutoff)
        if created_at > cutoff_date:
            return False

        # Keep if pinned
        if memory.get('pinned', False):
            return False

        # Keep if resolved error (has solution)
        if memory['type'] == 'error' and memory.get('resolved', False):
            return False

        # Keep if high access count (used frequently)
        if memory.get('access_count', 0) > 5:
            return False

        # Keep if high usefulness score
        if memory.get('usefulness_score', 0) > 0.7:
            return False

        # Keep if part of knowledge graph (has relations)
        if len(memory.get('relations', [])) > 0:
            return False

        # Keep decisions and patterns (valuable long-term)
        if memory['type'] in ['decision', 'pattern']:
            return False

        # Delete if:
        # - Old AND low access count AND low usefulness
        # - Unresolved errors (already fixed elsewhere)
        # - Temporary context
        if memory['type'] == 'context' and memory.get('access_count', 0) == 0:
            return True

        if memory['type'] == 'error' and not memory.get('resolved', False):
            return True

        if memory.get('usefulness_score', 0) < 0.3 and memory.get('access_count', 0) == 0:
            return True

        return False

    def prune(self, older_than_days: int = 30, max_delete: int = 1000):
        """Prune memories older than specified days"""
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        self.log(f"\n🧹 Memory Pruning {'(DRY RUN)' if self.dry_run else ''}")
        self.log(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d')}")
        self.log(f"Max deletions: {max_delete}\n")

        # Get all memories
        self.log("📊 Fetching memories...")
        response = self.api_request("/memories?limit=10000", 'GET')

        if not response:
            self.log("❌ Failed to fetch memories")
            return

        memories = response if isinstance(response, list) else []
        self.log(f"Found: {len(memories)} total memories\n")

        # Analyze each memory
        to_delete = []
        for item in memories:
            memory = item.get('memory', item)

            if self.should_delete(memory, cutoff_date):
                to_delete.append(memory)
                if len(to_delete) >= max_delete:
                    break
            else:
                self.kept_count += 1

        self.log(f"Analysis complete:")
        self.log(f"  ✓ Keep: {self.kept_count} memories")
        self.log(f"  ❌ Delete: {len(to_delete)} memories\n")

        if len(to_delete) == 0:
            self.log("✓ No memories to delete")
            return

        # Delete memories
        if not self.dry_run:
            self.log("Deleting memories...")
            for memory in to_delete:
                result = self.api_request(f"/memories/{memory['id']}", 'DELETE')
                if result:
                    self.deleted_count += 1
                    # Estimate bytes freed
                    content_size = len(memory.get('content', ''))
                    self.bytes_freed += content_size

                if self.deleted_count % 10 == 0:
                    print(f"  Deleted: {self.deleted_count}/{len(to_delete)}", end='\r')

            print()  # Newline after progress
            self.log(f"\n✓ Deleted: {self.deleted_count} memories")
            self.log(f"💾 Freed: ~{self.bytes_freed / 1024:.1f} KB")
        else:
            self.log("(Dry run - no deletions performed)")
            self.log("\nRun with --execute to perform actual deletions")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Prune old, low-value memories')
    parser.add_argument('--days', type=int, default=30,
                       help='Delete memories older than N days (default: 30)')
    parser.add_argument('--max', type=int, default=1000,
                       help='Maximum memories to delete (default: 1000)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually delete (default is dry-run)')

    args = parser.parse_args()

    # Check memory service
    try:
        req = urllib.request.Request(f"{MEMORY_API}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                print("❌ Memory service not available")
                sys.exit(1)
    except:
        print("❌ Cannot connect to memory service")
        sys.exit(1)

    # Run pruner
    pruner = MemoryPruner(dry_run=not args.execute)
    pruner.prune(older_than_days=args.days, max_delete=args.max)

if __name__ == '__main__':
    main()
