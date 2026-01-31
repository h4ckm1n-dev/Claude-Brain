#!/usr/bin/env python3
"""
Document Watcher - Auto-indexing service
Watches ~/Documents for changes and automatically indexes new/modified files
Runs in background, uses minimal resources
"""

import os
import sys
import time
import json
import hashlib
import signal
from pathlib import Path
from datetime import datetime
from typing import Set
import urllib.request
import urllib.error

# Configuration
MEMORY_API = "http://localhost:8100"
STATE_FILE = os.path.expanduser("~/.claude/memory/data/watch-state.json")
CHECK_INTERVAL = 30  # Check every 30 seconds
LOG_FILE = os.path.expanduser("~/.claude/memory/logs/watcher.log")
CONFIG_FILE = os.path.expanduser("~/.claude/memory/data/indexing-config.json")

# Import from index_documents
sys.path.insert(0, os.path.dirname(__file__))
from index_documents import DocumentIndexer, EXCLUDE_DIRS, SUPPORTED_EXTENSIONS

class DocumentWatcher:
    def __init__(self, check_interval=CHECK_INTERVAL):
        self.indexer = DocumentIndexer(use_state=True, force_reindex=False, parallel=False)
        self.running = True
        self.last_check = time.time()
        self.log_enabled = True
        self.check_interval = check_interval
        self.watch_folders = self.load_watch_folders()

        # Setup logging
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        # Handle graceful shutdown
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def load_watch_folders(self):
        """Load folders from config file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    folders = config.get('folders', [])
                    # Expand paths and filter to existing directories
                    expanded = []
                    for folder in folders:
                        expanded_path = os.path.expanduser(folder)
                        if os.path.isdir(expanded_path):
                            expanded.append(expanded_path)
                    return expanded if expanded else [os.path.expanduser("~/Documents")]
        except Exception as e:
            print(f"Warning: Could not load config, using default ~/Documents: {e}")

        # Default to ~/Documents if config not found
        return [os.path.expanduser("~/Documents")]

    def log(self, message: str):
        """Log message to file and stdout"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"

        if self.log_enabled:
            print(log_msg)

        try:
            with open(LOG_FILE, 'a') as f:
                f.write(log_msg + '\n')
        except:
            pass

    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        self.log("🛑 Shutting down document watcher...")
        self.running = False
        sys.exit(0)

    def check_memory_service(self) -> bool:
        """Check if memory service is available"""
        try:
            req = urllib.request.Request(f"{MEMORY_API}/health")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except:
            return False

    def get_modified_files(self) -> Set[Path]:
        """Get files modified since last check"""
        modified_files = set()
        cutoff_time = self.last_check

        # Scan all configured watch folders
        for watch_folder in self.watch_folders:
            for file_path in Path(watch_folder).rglob('*'):
                # Skip directories
                if file_path.is_dir():
                    continue

                # Skip excluded directories
                if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
                    continue

                # Check extension
                if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                try:
                    # Check if modified after last check
                    mtime = file_path.stat().st_mtime
                    if mtime > cutoff_time:
                        modified_files.add(file_path)
                except:
                    continue

        return modified_files

    def watch(self):
        """Main watch loop"""
        self.log("👁️  Document Watcher started")
        self.log(f"Watching {len(self.watch_folders)} folder(s):")
        for folder in self.watch_folders:
            self.log(f"  - {folder}")
        self.log(f"Check interval: {self.check_interval}s")
        self.log(f"Log file: {LOG_FILE}")

        # Do initial indexing pass for existing files
        self.log("🔍 Starting initial indexing pass...")
        # Set last_check to 0 to catch all existing files
        self.last_check = 0
        initial_files = self.get_modified_files()
        if initial_files:
            indexed = 0
            skipped = 0
            errors = 0

            self.log(f"📚 Found {len(initial_files)} existing file(s) to check")
            for file_path in initial_files:
                try:
                    result = self.indexer.index_file(file_path)
                    if result['success']:
                        indexed += 1
                        self.log(f"✓ Indexed: {file_path.name} ({result['chunks']} chunks)")
                    elif result['reason'] == 'unchanged':
                        skipped += 1  # Already indexed, no change
                    elif result['reason'] != 'no_text':
                        errors += 1
                        self.log(f"⊘ Skipped: {file_path.name} - {result['reason']}")
                except Exception as e:
                    errors += 1
                    self.log(f"❌ Error indexing {file_path.name}: {e}")

            self.log(f"📊 Initial scan complete: {indexed} indexed, {skipped} unchanged, {errors} errors")
        else:
            self.log("✓ No files to index (all up to date)")

        # Now start watching for changes
        self.last_check = time.time()
        self.log("👁️  Watching for changes...")

        while self.running:
            try:
                # Check if memory service is available
                if not self.check_memory_service():
                    self.log("⚠️  Memory service unavailable, waiting...")
                    time.sleep(self.check_interval)
                    continue

                # Get modified files
                modified_files = self.get_modified_files()

                if modified_files:
                    indexed = 0
                    skipped = 0
                    errors = 0

                    # Index each modified file
                    for file_path in modified_files:
                        try:
                            result = self.indexer.index_file(file_path)

                            if result['success']:
                                indexed += 1
                                self.log(f"✓ Indexed: {file_path.name} ({result['chunks']} chunks)")
                            elif result['reason'] == 'unchanged':
                                skipped += 1  # File hash unchanged
                            elif result['reason'] != 'no_text':
                                errors += 1
                                self.log(f"⊘ Skipped: {file_path.name} - {result['reason']}")
                        except Exception as e:
                            errors += 1
                            self.log(f"❌ Error indexing {file_path.name}: {e}")

                    if indexed > 0 or errors > 0:
                        self.log(f"📝 Checked {len(modified_files)} file(s): {indexed} indexed, {skipped} unchanged, {errors} errors")

                # Update last check time
                self.last_check = time.time()

                # Sleep until next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                self.shutdown(None, None)
            except Exception as e:
                self.log(f"❌ Watcher error: {e}")
                time.sleep(self.check_interval)

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Auto-index documents on file changes')
    parser.add_argument('--interval', type=int, default=CHECK_INTERVAL,
                       help=f'Check interval in seconds (default: {CHECK_INTERVAL})')
    parser.add_argument('--quiet', action='store_true',
                       help='Disable stdout logging (log file only)')

    args = parser.parse_args()

    # Create watcher with custom interval
    watcher = DocumentWatcher(check_interval=args.interval)
    watcher.log_enabled = not args.quiet

    # Check memory service before starting
    if not watcher.check_memory_service():
        print("❌ Memory service not available. Start it first:")
        print("   cd ~/.claude/memory && docker compose up -d")
        sys.exit(1)

    # Start watching
    watcher.watch()

if __name__ == '__main__':
    main()
