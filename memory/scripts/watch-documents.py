#!/usr/bin/env python3
"""
Document Watcher - Continuous RAG Indexing
Watches ~/Documents for changes and auto-indexes new/modified files
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Set, Dict
import urllib.request
import urllib.error
import subprocess

# Import the indexer
sys.path.insert(0, os.path.dirname(__file__))
from index_documents import DocumentIndexer, DOCUMENTS_ROOT, MEMORY_API, SUPPORTED_EXTENSIONS, EXCLUDE_DIRS

# Polling interval
POLL_INTERVAL = 10  # seconds
STATE_FILE = os.path.expanduser("~/.claude/memory/data/watch-state.json")


class DocumentWatcher:
    def __init__(self, poll_interval: int = 10):
        self.indexer = DocumentIndexer()
        self.indexed_files: Dict[str, str] = {}  # path -> hash
        self.poll_interval = poll_interval
        self.load_state()

    def load_state(self):
        """Load previously indexed files state"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    self.indexed_files = json.load(f)
                print(f"📂 Loaded state: {len(self.indexed_files)} previously indexed files")
        except Exception as e:
            print(f"⚠️  Could not load state: {e}")
            self.indexed_files = {}

    def save_state(self):
        """Save indexed files state"""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump(self.indexed_files, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save state: {e}")

    def get_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file"""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def should_index(self, file_path: Path) -> bool:
        """Check if file should be indexed"""
        # Use indexer's logic
        if not self.indexer.should_index_file(file_path):
            return False

        # Check if file exists and is readable
        if not file_path.exists() or not file_path.is_file():
            return False

        return True

    def scan_for_changes(self) -> Set[Path]:
        """Scan Documents folder for new/modified files"""
        new_or_modified = set()

        for file_path in Path(DOCUMENTS_ROOT).rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip excluded directories
            if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
                continue

            # Skip unsupported extensions
            if not self.should_index(file_path):
                continue

            file_str = str(file_path)
            current_hash = self.get_file_hash(file_path)

            if not current_hash:
                continue

            # Check if new or modified
            if file_str not in self.indexed_files:
                # New file
                new_or_modified.add(file_path)
                print(f"🆕 New file detected: {file_path.relative_to(DOCUMENTS_ROOT)}")
            elif self.indexed_files[file_str] != current_hash:
                # Modified file
                new_or_modified.add(file_path)
                print(f"📝 Modified file detected: {file_path.relative_to(DOCUMENTS_ROOT)}")

        return new_or_modified

    def delete_old_chunks(self, file_path: Path):
        """Delete old chunks of a file from memory system"""
        try:
            # Get all memories for this file
            req = urllib.request.Request(f"{MEMORY_API}/memories")
            with urllib.request.urlopen(req, timeout=10) as response:
                memories = json.loads(response.read())

            # Find chunks from this file
            file_str = str(file_path)
            to_delete = []

            for memory in memories:
                if memory.get('source') == file_str:
                    to_delete.append(memory['id'])

            # Delete old chunks
            for memory_id in to_delete:
                try:
                    req = urllib.request.Request(
                        f"{MEMORY_API}/memories/{memory_id}",
                        method='DELETE'
                    )
                    urllib.request.urlopen(req, timeout=5)
                except Exception as e:
                    print(f"⚠️  Could not delete old chunk {memory_id}: {e}")

            if to_delete:
                print(f"  🗑️  Deleted {len(to_delete)} old chunks")

        except Exception as e:
            print(f"⚠️  Error cleaning old chunks: {e}")

    def index_file(self, file_path: Path):
        """Index a single file and update state"""
        try:
            # Delete old chunks if file was previously indexed
            file_str = str(file_path)
            if file_str in self.indexed_files:
                self.delete_old_chunks(file_path)

            # Index the file
            if self.indexer.index_file(file_path):
                # Update state
                self.indexed_files[file_str] = self.get_file_hash(file_path)
                self.save_state()
                return True

            return False

        except Exception as e:
            print(f"❌ Error indexing {file_path}: {e}")
            return False

    def watch(self):
        """Main watch loop"""
        print("\n" + "="*60)
        print("👁️  Document Watcher - RAG Auto-Indexing")
        print("="*60)
        print(f"Watching: {DOCUMENTS_ROOT}")
        print(f"Poll interval: {self.poll_interval}s")
        print(f"Supported: {len(SUPPORTED_EXTENSIONS)} file types")
        print("="*60 + "\n")

        # Initial scan
        print("🔍 Initial scan for changes...")
        changes = self.scan_for_changes()

        if changes:
            print(f"\n📦 Found {len(changes)} new/modified files")
            for file_path in changes:
                self.index_file(file_path)
        else:
            print("✓ No changes detected\n")

        print("👁️  Watching for changes... (Ctrl+C to stop)\n")

        # Watch loop
        try:
            while True:
                time.sleep(self.poll_interval)

                changes = self.scan_for_changes()
                if changes:
                    print(f"\n📦 Detected {len(changes)} changes at {datetime.now().strftime('%H:%M:%S')}")
                    for file_path in changes:
                        self.index_file(file_path)
                    print()

        except KeyboardInterrupt:
            print("\n\n⚠️  Watcher stopped by user")
            self.save_state()

        except Exception as e:
            print(f"\n\n❌ Watcher error: {e}")
            self.save_state()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Watch and auto-index documents')
    parser.add_argument('--interval', type=int, default=10, help='Poll interval in seconds (default: 10)')

    args = parser.parse_args()

    poll_interval = args.interval

    # Check if memory service is available
    try:
        req = urllib.request.Request(f"{MEMORY_API}/health")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                print("❌ Memory service not available. Start it first:")
                print("   cd ~/.claude/memory && docker compose up -d")
                sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to memory service: {e}")
        print("   Start it: cd ~/.claude/memory && docker compose up -d")
        sys.exit(1)

    # Run watcher
    watcher = DocumentWatcher(poll_interval=poll_interval)
    watcher.watch()


if __name__ == '__main__':
    main()
