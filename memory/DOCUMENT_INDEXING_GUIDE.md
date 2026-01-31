# Document RAG Indexing System

Index your entire ~/Documents folder for Claude to search and reference.

---

## 🚀 Quick Start

### 1. Test with Sample (10 files)
```bash
cd ~/.claude/memory/scripts
python3 index-documents.py --test
```

### 2. Index Everything
```bash
python3 index-documents.py
```

### 3. Index Specific Folder
```bash
python3 index-documents.py --path ~/Documents/Projects
```

---

## 📦 Optional Dependencies (for better support)

Install these for PDF, DOCX, RTF support:
```bash
pip3 install --break-system-packages --user PyPDF2 python-docx striprtf requests
```

**Without these**, the indexer will still work for:
- ✅ Plain text (.txt, .md, .log)
- ✅ Code files (.py, .js, .ts, .java, .go, .rs, etc.)
- ✅ Config files (.json, .yml, .yaml, .toml, .ini)
- ✅ HTML/XML files
- ✅ CSV/TSV files
- ✅ Shell scripts (.sh, .bash, .zsh)

**With dependencies**, you also get:
- 📄 PDF files (.pdf)
- 📝 Word documents (.docx, .doc)
- 📋 RTF files (.rtf)

---

## 🎯 What Gets Indexed

### Supported File Types (30+)
**Documents:**
- .txt, .md, .markdown, .rst
- .pdf (with PyPDF2)
- .docx, .doc (with python-docx)
- .rtf (with striprtf)

**Code:**
- .py, .js, .ts, .jsx, .tsx
- .java, .c, .cpp, .h, .go, .rs
- .sh, .bash, .zsh
- .sql

**Data:**
- .json, .yml, .yaml, .toml
- .csv, .tsv
- .xml, .html, .htm

**Config:**
- .conf, .config, .ini
- .env.example, .gitignore
- .log

### Automatically Excluded

**Directories:**
- .git, node_modules, __pycache__
- .venv, venv, dist, build
- .idea, .vscode, .DS_Store
- Library, Applications, .Trash

**File Types:**
- Binaries (.exe, .bin, .so, .dll)
- Images (.jpg, .png, .gif, .svg)
- Media (.mp3, .mp4, .avi, .mov)
- Archives (.zip, .tar, .gz, .rar)
- Databases (.db, .sqlite)

**Sensitive Files:**
- Files with "password", "secret", "token", "key" in name
- .env files (except .env.example)
- credential files

---

## 🔍 How Chunking Works

**Large files are split into chunks:**
- Chunk size: 2000 characters
- Overlap: 200 characters (for context)
- Breaks at sentence boundaries when possible

**Example:**
- 10KB file → ~5 chunks
- Each chunk stored separately with metadata
- Search returns relevant chunks with source file info

---

## 📊 What Gets Stored

For each document chunk:

```json
{
  "type": "docs",
  "content": "...chunk text...",
  "tags": ["document", "indexed", "category", "file-extension"],
  "project": "Documents/Projects",
  "source": "/Users/you/Documents/file.md",
  "context": {
    "file_name": "file.md",
    "relative_path": "Projects/file.md",
    "extension": ".md",
    "size_bytes": 12345,
    "modified_at": "2026-01-29T...",
    "chunk_index": 0,
    "total_chunks": 3,
    "file_hash": "abc123..."
  }
}
```

---

## 🔎 Searching Your Documents

### Via MCP Tools (in Claude conversation)
```typescript
// Search across all indexed documents
search_memory({
  query: "docker deployment configuration",
  limit: 10
})

// Filter by project/category
search_memory({
  query: "API authentication",
  limit: 5,
  tags: ["Projects"]  // Matches Documents/Projects/*
})

// Find specific file type
search_memory({
  query: "database schema",
  limit: 5,
  tags: ["sql"]
})
```

### Via API
```bash
# Search
curl -s http://localhost:8100/memories/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "kubernetes deployment",
    "limit": 10,
    "search_mode": "hybrid"
  }' | jq

# Filter by tags
curl -s http://localhost:8100/memories \
  -G --data-urlencode "tags=document,pdf" | jq
```

### Via Dashboard
Open: http://localhost:5173
- Navigate to "Search" page
- Enter query
- Filter by type, tags, project
- View source file and chunk info

---

## 🔄 Re-indexing Strategy

### When to Re-index
- Files added/modified in Documents folder
- Want to update chunks for changed files
- Added new file types support

### Incremental Re-index
Currently, the indexer does NOT check for duplicates automatically.

**To re-index:**
1. Delete old document memories
2. Run indexer again

```bash
# Delete all indexed documents (careful!)
curl -s http://localhost:8100/memories | \
  jq -r '.[] | select(.tags | contains(["indexed"])) | .id' | \
  while read id; do
    curl -X DELETE "http://localhost:8100/memories/$id"
  done

# Re-index
python3 index-documents.py
```

### Scheduled Re-indexing
Create a cron job (weekly):
```bash
# Edit crontab
crontab -e

# Add: Run every Sunday at 2am
0 2 * * 0 cd ~/.claude/memory/scripts && python3 index-documents.py >> ~/Documents/indexing.log 2>&1
```

---

## 📈 Performance & Limits

**Indexing Speed:**
- ~50-100 files/minute (depends on file size)
- Large PDFs slower (~10-20/minute)

**Storage:**
- ~1KB per chunk in Qdrant
- 1000 files (~2MB each, 2 chunks avg) = ~2MB vector DB

**Limits:**
- Max file size: 50MB (configurable)
- Max PDF pages: 100 (configurable)
- Chunk size: 2000 chars (configurable)

**Recommended:**
- Start with `--test` (10 files)
- Check quality before full index
- Use `--max-files 100` for batches

---

## 🎯 Use Cases

### 1. Document Search
**Query:** "How to deploy with Docker?"
**Returns:** Chunks from deployment guides, docker-compose files, README files

### 2. Code Examples
**Query:** "React authentication hook"
**Returns:** Your custom hooks, auth implementations from past projects

### 3. Configuration Reference
**Query:** "nginx SSL configuration"
**Returns:** Your nginx config files with SSL setup

### 4. Meeting Notes
**Query:** "Q3 planning decisions"
**Returns:** Meeting notes, decision docs from that period

### 5. Generate New Docs
**Query:** "Create a deployment guide based on my existing docs"
**Claude:** Searches indexed docs, synthesizes new guide using your patterns

---

## 🛠 Troubleshooting

### "Memory service not available"
```bash
cd ~/.claude/memory
docker compose up -d
```

### "Permission denied"
```bash
chmod +x ~/.claude/memory/scripts/index-documents.py
```

### PDF/DOCX not indexing
```bash
# Install optional dependencies
pip3 install --break-system-packages --user PyPDF2 python-docx striprtf
```

### Too many files
```bash
# Index in batches
python3 index-documents.py --max-files 500
# Wait, then run again (will index next batch)
```

### Slow indexing
- Large PDFs are slow (OCR + extraction)
- Lots of small files is fast
- Network-mounted drives slower

---

## 📝 Example Session

```bash
# 1. Test with 10 files
$ python3 index-documents.py --test

🔍 Scanning: /Users/you/Documents
✓ Indexed: Projects/myapp/README.md (2 chunks)
✓ Indexed: Notes/meeting-2026-01.md (1 chunks)
✓ Indexed: Guides/docker-setup.md (3 chunks)
...
📊 Indexed: 10 files (25 chunks)

# 2. Search from Claude
User: "Find my Docker Compose examples"

Claude: [Uses search_memory(query="docker compose")]
Returns:
- Projects/backend/docker-compose.yml (chunk 0/1)
- Guides/docker-setup.md (chunk 1/3)
- Notes/deployment-notes.md (chunk 0/2)

# 3. Generate new doc
User: "Create a Docker deployment guide for my new project using my existing patterns"

Claude: [Searches indexed docs, finds your patterns, generates guide]
Generated:
- Uses your compose file structure
- Includes your Traefik patterns
- References your environment setup
- Follows your documentation style
```

---

## 🎨 Advanced: Custom Filters

Edit `index-documents.py` to customize:

```python
# Line 19-25: Exclude more directories
EXCLUDE_DIRS = {
    '.git', 'node_modules',
    'MyPrivateFolder',  # Add custom excludes
}

# Line 32-36: Exclude file extensions
EXCLUDE_EXTENSIONS = {
    '.exe', '.mp4',
    '.backup',  # Add custom excludes
}

# Line 12-13: Change chunking
CHUNK_SIZE = 3000  # Larger chunks
OVERLAP = 300      # More overlap
```

---

**Your entire Documents folder is now searchable!** 📚✨

Claude can now:
- ✅ Search across all your documents
- ✅ Find relevant examples and patterns
- ✅ Reference your existing work
- ✅ Generate new content based on your style
- ✅ Answer questions from your knowledge base
