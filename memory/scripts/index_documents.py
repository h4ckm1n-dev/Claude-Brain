#!/usr/bin/env python3
"""
Document Indexer for RAG System (Enhanced)
Indexes documents into the DOCUMENTS collection (separate from memories)
Features: Progress bars, parallel processing, smart chunking, state tracking
Supports: .txt, .md, .pdf, .docx, .doc, .rtf, .html, .json, .yml, .yaml, code files

Documents = Filesystem content for retrieval
Memories = Structured knowledge (errors, decisions, patterns)
"""

import os
import sys
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
DOCUMENTS_ROOT = None  # Will be set dynamically based on --path argument
MEMORY_API = "http://localhost:8100"
CHUNK_SIZE = 2000  # Characters per chunk
OVERLAP = 200  # Overlap between chunks
STATE_FILE = os.path.expanduser("~/.claude/memory/data/watch-state.json")
MAX_WORKERS = 4  # Parallel processing threads

# Exclude patterns
EXCLUDE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv',
    '.idea', '.vscode', 'dist', 'build', '.DS_Store',
    'Library', 'Applications', '.Trash', '.next', 'coverage',
    '.turbo', '.vercel', 'out', '.nuxt', '.cache', 'target',
    '.gradle', '.cargo', '__MACOSX'
}

EXCLUDE_EXTENSIONS = {
    '.exe', '.bin', '.so', '.dylib', '.dll',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
    '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.db', '.sqlite', '.lock', '.pyc', '.class'
}

# Supported file types
SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.markdown', '.rst',
    '.pdf', '.docx', '.doc', '.rtf',
    '.html', '.htm', '.xml',
    '.json', '.yml', '.yaml', '.toml',
    '.csv', '.tsv',
    '.sh', '.bash', '.zsh',
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.java', '.c', '.cpp', '.h', '.hpp', '.go', '.rs', '.rb', '.php',
    '.sql', '.env.example', '.gitignore',
    '.log', '.conf', '.config', '.ini', '.dockerfile'
}


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"


def format_time(seconds: float) -> str:
    """Format seconds to human-readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


class DocumentIndexer:
    def __init__(self, root_path, use_state=True, force_reindex=False, parallel=False):
        self.root_path = Path(root_path).expanduser().resolve()
        self.indexed_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.total_chunks = 0
        self.total_bytes = 0
        self.use_state = use_state
        self.force_reindex = force_reindex
        self.parallel = parallel
        self.indexed_files = {}  # path -> hash
        self.start_time = time.time()

        # Load state if enabled
        if self.use_state:
            self.load_state()

    def load_state(self):
        """Load previously indexed files from state file"""
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

    def extract_text(self, file_path: Path) -> Optional[str]:
        """Extract text from various file types"""
        ext = file_path.suffix.lower()

        try:
            # Plain text files
            if ext in {'.txt', '.md', '.markdown', '.rst', '.log', '.sh', '.bash', '.zsh',
                       '.json', '.yml', '.yaml', '.toml', '.csv', '.tsv', '.xml', '.html', '.htm',
                       '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
                       '.go', '.rs', '.rb', '.php', '.sql', '.conf', '.config', '.ini', '.gitignore',
                       '.dockerfile'}:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()

            # PDF files
            elif ext == '.pdf':
                try:
                    import PyPDF2
                    text = []
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages[:100]:  # Limit to 100 pages
                            text.append(page.extract_text())
                    return '\n'.join(text)
                except ImportError:
                    return None
                except Exception as e:
                    print(f"⚠️  Error reading PDF {file_path.name}: {e}")
                    return None

            # DOCX files
            elif ext == '.docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    return '\n'.join([para.text for para in doc.paragraphs])
                except ImportError:
                    return None
                except Exception as e:
                    print(f"⚠️  Error reading DOCX {file_path.name}: {e}")
                    return None

            # RTF files
            elif ext == '.rtf':
                try:
                    from striprtf.striprtf import rtf_to_text
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return rtf_to_text(f.read())
                except ImportError:
                    return None
                except Exception as e:
                    print(f"⚠️  Error reading RTF {file_path.name}: {e}")
                    return None

            else:
                return None

        except Exception as e:
            print(f"❌ Error extracting text from {file_path.name}: {e}")
            return None

    def chunk_text(self, text: str, file_path: Path) -> List[Dict]:
        """Split large text into overlapping chunks"""
        if len(text) <= CHUNK_SIZE:
            return [{'content': text, 'chunk_index': 0, 'total_chunks': 1}]

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + CHUNK_SIZE

            # Try to break at sentence boundary
            if end < len(text):
                for i in range(end, max(start + CHUNK_SIZE - 200, start), -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append({
                    'content': chunk,
                    'chunk_index': chunk_index,
                    'total_chunks': 0
                })
                chunk_index += 1

            start = end - OVERLAP if end < len(text) else end

        # Update total_chunks
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)

        return chunks

    def get_file_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from file"""
        stat = file_path.stat()
        relative_path = file_path.relative_to(self.root_path)
        parts = relative_path.parts
        category = parts[0] if len(parts) > 1 else "root"

        return {
            'file_path': str(file_path),
            'relative_path': str(relative_path),
            'file_name': file_path.name,
            'extension': file_path.suffix,
            'size_bytes': stat.st_size,
            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'category': category
        }

    def compute_hash(self, file_path: Path) -> str:
        """Compute file hash for deduplication"""
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def index_file(self, file_path: Path) -> Dict[str, any]:
        """Index a single file into memory system"""
        result = {'success': False, 'chunks': 0, 'bytes': 0, 'reason': ''}
        file_str = str(file_path)

        # Check if already indexed (unless force reindex)
        if self.use_state and not self.force_reindex:
            current_hash = self.compute_hash(file_path)
            if not current_hash:
                result['reason'] = 'hash_error'
                return result

            if file_str in self.indexed_files:
                if self.indexed_files[file_str] == current_hash:
                    result['reason'] = 'unchanged'
                    return result

        # Extract text
        text = self.extract_text(file_path)
        if not text or len(text.strip()) < 50:
            result['reason'] = 'no_text'
            return result

        # Get metadata
        metadata = self.get_file_metadata(file_path)
        file_hash = self.compute_hash(file_path)
        chunks = self.chunk_text(text, file_path)

        # Store each chunk
        for chunk_data in chunks:
            chunk_content = chunk_data['content']
            chunk_index = chunk_data['chunk_index']
            total_chunks = chunk_data['total_chunks']

            # Prepare tags
            tags = [
                'document',
                'indexed',
                metadata['category'],
                file_path.suffix[1:] if file_path.suffix else 'unknown',
            ]

            # Add directory tags
            for part in file_path.relative_to(self.root_path).parts[:-1]:
                if part not in EXCLUDE_DIRS:
                    tags.append(part)

            # Prepare document data (now separate from memories)
            document_data = {
                'content': chunk_content,
                'file_path': metadata['file_path'],
                'chunk_index': chunk_index,
                'total_chunks': total_chunks,
                'metadata': {
                    'file_name': metadata['file_name'],
                    'relative_path': metadata['relative_path'],
                    'file_type': metadata['extension'],
                    'folder': os.path.dirname(metadata['file_path']),
                    'size_bytes': metadata['size_bytes'],
                    'modified_at': metadata['modified_at'],
                    'file_hash': file_hash,
                    'category': metadata['category'],
                    'tags': tags
                }
            }

            # Store in documents collection (separate from memories)
            try:
                req = urllib.request.Request(
                    f"{MEMORY_API}/documents/insert",
                    data=json.dumps(document_data).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status not in [200, 201]:
                        result['reason'] = 'api_error'
                        return result
            except Exception as e:
                result['reason'] = f'api_error: {str(e)[:50]}'
                return result

        # Update state
        if self.use_state:
            self.indexed_files[file_str] = file_hash
            self.save_state()

        result['success'] = True
        result['chunks'] = len(chunks)
        result['bytes'] = metadata['size_bytes']
        return result

    def should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed"""
        # Check extension
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return False

        # Check if excluded
        if file_path.suffix.lower() in EXCLUDE_EXTENSIONS:
            return False

        # Check size (skip files > 50MB)
        try:
            if file_path.stat().st_size > 50 * 1024 * 1024:
                return False
        except:
            return False

        # Check if file contains sensitive data
        sensitive_patterns = ['password', 'secret', 'token', 'key', 'credential', '.env']
        name_lower = file_path.name.lower()
        if any(pattern in name_lower for pattern in sensitive_patterns):
            if file_path.suffix != '.example':
                return False

        return True

    def index_directory(self, root_path: Path, max_files: Optional[int] = None):
        """Recursively index all files in directory"""
        print(f"\n🔍 Scanning: {root_path}")
        print(f"Exclude dirs: {len(EXCLUDE_DIRS)} patterns")
        print(f"Supported: {len(SUPPORTED_EXTENSIONS)} file types")

        # Collect files first
        files_to_index = []
        for file_path in root_path.rglob('*'):
            if file_path.is_dir():
                continue
            if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
                continue
            if not self.should_index_file(file_path):
                continue
            files_to_index.append(file_path)
            if max_files and len(files_to_index) >= max_files:
                break

        total_files = len(files_to_index)
        print(f"Found: {total_files} files to process\n")

        if total_files == 0:
            print("No files to index.")
            return

        # Process files
        processed = 0
        try:
            if self.parallel:
                # Parallel processing
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {executor.submit(self.index_file, fp): fp for fp in files_to_index}

                    for future in as_completed(futures):
                        file_path = futures[future]
                        processed += 1
                        try:
                            result = future.result()
                            self._update_stats(result, file_path, processed, total_files)
                        except Exception as e:
                            print(f"❌ Error processing {file_path.name}: {e}")
                            self.error_count += 1
            else:
                # Sequential processing
                for file_path in files_to_index:
                    processed += 1
                    try:
                        result = self.index_file(file_path)
                        self._update_stats(result, file_path, processed, total_files)
                    except KeyboardInterrupt:
                        print("\n\n⚠️  Indexing interrupted by user")
                        break
                    except Exception as e:
                        print(f"❌ Error processing {file_path.name}: {e}")
                        self.error_count += 1

        except Exception as e:
            print(f"❌ Fatal error: {e}")

        self._print_summary()

    def _update_stats(self, result: Dict, file_path: Path, processed: int, total: int):
        """Update statistics and print progress"""
        if result['success']:
            self.indexed_count += 1
            self.total_chunks += result['chunks']
            self.total_bytes += result['bytes']

            # Progress indicator
            percent = (processed / total) * 100
            elapsed = time.time() - self.start_time
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / rate if rate > 0 else 0

            print(f"[{percent:5.1f}%] ✓ {file_path.name[:40]:40} "
                  f"({result['chunks']} chunks, {format_size(result['bytes'])}) "
                  f"| {rate:.1f} files/s | ETA: {format_time(eta)}")
        elif result['reason'] == 'unchanged':
            self.skipped_count += 1
        else:
            if result['reason'] != 'no_text':
                print(f"[{(processed/total)*100:5.1f}%] ⊘ {file_path.name[:40]:40} - {result['reason']}")
            self.error_count += 1

    def _print_summary(self):
        """Print indexing summary"""
        elapsed = time.time() - self.start_time
        total_processed = self.indexed_count + self.skipped_count + self.error_count

        print(f"\n{'='*70}")
        print(f"📊 Indexing Complete in {format_time(elapsed)}")
        print(f"{'='*70}")
        print(f"✓ Indexed:  {self.indexed_count:,} files ({format_size(self.total_bytes)})")
        print(f"📦 Chunks:   {self.total_chunks:,} total")
        print(f"⊘ Skipped:  {self.skipped_count:,} files (unchanged)")
        print(f"❌ Errors:   {self.error_count:,} files")
        print(f"⚡ Speed:    {total_processed/elapsed if elapsed > 0 else 0:.1f} files/s")
        print(f"{'='*70}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Index documents into RAG memory system (Enhanced)')
    parser.add_argument('--path', default=os.path.expanduser("~/Documents"), help='Path to index (default: ~/Documents)')
    parser.add_argument('--max-files', type=int, help='Maximum files to index (for testing)')
    parser.add_argument('--test', action='store_true', help='Test mode: index only 10 files')
    parser.add_argument('--force', action='store_true', help='Force re-index all files (even if already indexed)')
    parser.add_argument('--no-state', action='store_true', help='Disable state tracking (always index everything)')
    parser.add_argument('--parallel', action='store_true', help='Use parallel processing (faster)')

    args = parser.parse_args()

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

    # Run indexer
    use_state = not args.no_state
    force_reindex = args.force
    parallel = args.parallel
    indexer = DocumentIndexer(root_path=args.path, use_state=use_state, force_reindex=force_reindex, parallel=parallel)
    max_files = 10 if args.test else args.max_files

    print("\n" + "="*70)
    print("📚 Document Indexer - RAG System (Enhanced)")
    print("="*70)
    print(f"Root:       {args.path}")
    print(f"API:        {MEMORY_API}")
    print(f"Chunk size: {CHUNK_SIZE} chars (overlap: {OVERLAP})")
    print(f"Mode:       {'Parallel' if parallel else 'Sequential'}")
    if max_files:
        print(f"Max files:  {max_files}")
    print("="*70)

    indexer.index_directory(Path(args.path), max_files=max_files)

    print("\n🎯 Usage:")
    print("   Search:    mcp search_documents query='your topic'")
    print("   Dashboard: http://localhost:8100 (Documents page)")
    print("   API:       curl http://localhost:8100/documents/search?query=topic")


if __name__ == '__main__':
    main()
