#!/usr/bin/env python3
"""
Cleanup Low-Quality Memories
Removes useless auto-captured memories that contain no valuable information.
"""

import json
import sys
import urllib.request
import urllib.error

import os
MEMORY_API = os.environ.get("MEMORY_SERVICE_URL", "http://claude-mem-frontend:80")

def get_all_memories():
    """Fetch all memories"""
    try:
        req = urllib.request.Request(f"{MEMORY_API}/memories?limit=10000")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("items", data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Error fetching memories: {e}")
        sys.exit(1)

def is_low_quality(memory):
    """Check if memory is low quality"""
    content = memory.get('content', '').strip()
    tags = memory.get('tags', [])

    # Too short
    if len(content) < 20:
        return True, "Content too short"

    # Useless session summaries
    if "session-end" in tags:
        if "Duration: unknown" in content:
            # Check if it has any actual work info
            if "Files edited: 0" in content or "Files edited:" not in content:
                return True, "Empty session summary"

    # Generic patterns
    useless_patterns = [
        "Session ended (session_end) - Duration: unknown.",
        "Duration: unknown.",
    ]

    for pattern in useless_patterns:
        if content == pattern:
            return True, "Generic/empty content"

    return False, None

def cleanup_memories(dry_run=True):
    """Find and delete low-quality memories"""
    print(f"🔍 Fetching memories...")
    memories = get_all_memories()
    print(f"Found {len(memories)} total memories\n")

    to_delete = []

    for memory in memories:
        is_bad, reason = is_low_quality(memory)
        if is_bad:
            to_delete.append({
                'id': memory['id'],
                'content': memory['content'][:80] + ('...' if len(memory['content']) > 80 else ''),
                'reason': reason
            })

    if not to_delete:
        print("✅ No low-quality memories found!")
        return

    print(f"⚠️  Found {len(to_delete)} low-quality memories:\n")
    for item in to_delete:
        print(f"  • {item['content']}")
        print(f"    Reason: {item['reason']}")
        print(f"    ID: {item['id']}\n")

    if dry_run:
        print(f"🔍 DRY RUN - No memories deleted")
        print(f"Run with --execute to actually delete these memories")
        return

    # Actually delete
    print(f"🗑️  Deleting {len(to_delete)} memories...")
    deleted = 0
    errors = 0

    for item in to_delete:
        try:
            req = urllib.request.Request(
                f"{MEMORY_API}/memories/{item['id']}",
                method='DELETE'
            )
            with urllib.request.urlopen(req) as response:
                deleted += 1
                print(f"  ✓ Deleted: {item['content'][:60]}...")
        except Exception as e:
            errors += 1
            print(f"  ✗ Error: {item['id']} - {e}")

    print(f"\n📊 Cleanup complete: {deleted} deleted, {errors} errors")

if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    cleanup_memories(dry_run=dry_run)
