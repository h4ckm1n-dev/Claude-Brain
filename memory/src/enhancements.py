"""Advanced memory quality enhancements.

Features:
- Semantic deduplication (prevent duplicate knowledge)
- Automatic tag suggestions from similar memories
- Template-based validation hints
- Keyphrase extraction (YAKE) for better tags and embeddings
- Enriched embedding text builder
"""

import logging
import unicodedata
import re as _re_module
from typing import Optional
from collections import defaultdict

from .models import MemoryCreate, MemoryType
from . import collections
from .embeddings import embed_text

logger = logging.getLogger(__name__)


# ============================================================================
# YAKE Keyphrase Extractor (lazy-loaded singleton)
# ============================================================================

_yake_extractor = None


def _get_yake_extractor():
    """Lazy-load YAKE extractor (avoids import cost at module load)."""
    global _yake_extractor
    if _yake_extractor is None:
        try:
            import yake
            _yake_extractor = yake.KeywordExtractor(
                lan="en",
                n=3,           # max ngram size
                dedupLim=0.7,  # dedup threshold
                top=10,        # max keyphrases
                features=None,
            )
        except ImportError:
            logger.warning("YAKE not installed — keyphrase extraction disabled")
            _yake_extractor = "disabled"
    return _yake_extractor


def extract_keyphrases(text: str, top_n: int = 8) -> list[str]:
    """Extract key phrases from text using YAKE (unsupervised, fast).

    Returns list of keyphrases sorted by relevance (lower YAKE score = more relevant).
    Returns empty list if YAKE is unavailable.
    """
    extractor = _get_yake_extractor()
    if extractor == "disabled" or not text or len(text) < 30:
        return []

    try:
        keywords = extractor.extract_keywords(text)
        # YAKE returns (keyphrase, score) — lower score = more relevant
        return [kw for kw, _score in keywords[:top_n]]
    except Exception as exc:
        logger.debug(f"Keyphrase extraction failed: {exc}")
        return []


# ============================================================================
# Template-Based Validation Hints
# ============================================================================

MEMORY_TEMPLATES = {
    MemoryType.ERROR: {
        "required_fields": ["error_message", "solution OR prevention"],
        "suggested_structure": """
Problem: [What went wrong]
Error: [Actual error message]
Cause: [Why it happened]
Solution: [How to fix]
Prevention: [How to avoid in future]
        """.strip(),
        "example": """
PostgreSQL connection timeout: Database max_connections=100 was exceeded during peak load.
Error: psycopg2.OperationalError: FATAL: remaining connection slots are reserved
Cause: Connection pool not properly sized for concurrent requests
Solution: Increased max_connections to 200 and configured pgbouncer connection pooling
Prevention: Monitor connection usage with pg_stat_activity, set up alerts at 80% capacity
        """.strip()
    },

    MemoryType.DECISION: {
        "required_fields": ["rationale", "alternatives"],
        "suggested_structure": """
Decision: [What was chosen]
Rationale: [Why this choice]
Alternatives: [What else was considered]
Trade-offs: [Pros and cons]
Impact: [Expected consequences]
        """.strip(),
        "example": """
Decision: Use PostgreSQL instead of MongoDB for Enduro project database
Rationale: Need ACID compliance for financial transactions, strong JSON support via jsonb, excellent PostGIS for location data
Alternatives: MongoDB (document flexibility but weak transactions), MySQL (mature but limited JSON), SQLite (simple but not concurrent)
Trade-offs: More complex than document DBs, requires schema migrations, but gains data integrity
Impact: Enables reliable booking system, supports complex queries, integrates with existing Python/Django ecosystem
        """.strip()
    },

    MemoryType.PATTERN: {
        "required_fields": ["context", "example"],
        "suggested_structure": """
Pattern: [Name and description]
When to use: [Scenarios]
How it works: [Implementation approach]
Example: [Code or concrete example]
Benefits: [Why use this]
Drawbacks: [When not to use]
        """.strip(),
        "example": """
Pattern: Retry with exponential backoff for external API calls
When to use: Calling unreliable third-party APIs, network operations, distributed systems
How it works: On failure, wait 1s, then 2s, 4s, 8s... up to max retries before giving up
Example: @retry(max_attempts=5, backoff_factor=2, max_delay=30) async def fetch_api()
Benefits: Handles transient failures, prevents thundering herd, gives services time to recover
Drawbacks: Adds latency on failures, can mask persistent issues, needs timeout limits
        """.strip()
    },

    MemoryType.DOCS: {
        "required_fields": ["source"],
        "suggested_structure": """
Topic: [What this documents]
Source: [URL or reference]
Key Points: [Summary of important info]
When Useful: [Scenarios where you'd need this]
Version: [Library/API version if applicable]
        """.strip(),
        "example": """
Topic: Qdrant hybrid search with dense + sparse vectors
Source: https://qdrant.tech/documentation/concepts/search/#hybrid-search
Key Points: Combine semantic (dense) + keyword (sparse) search for best results. Use query(query=vector, prefetch=[sparse_query]) pattern. Fusion methods: RRF (rank reciprocal fusion) or weighted.
When Useful: When semantic search misses exact keywords or keyword search misses similar concepts
Version: Qdrant v1.7+
        """.strip()
    },

    MemoryType.LEARNING: {
        "required_fields": [],
        "suggested_structure": """
Learning: [What you learned]
Context: [Why this was surprising/useful]
Example: [Concrete scenario]
Impact: [How this changes your approach]
        """.strip(),
        "example": """
Learning: Docker healthcheck dependencies prevent race conditions in multi-service apps
Context: Claude Brain Neo4j service was failing on startup because Qdrant wasn't ready yet
Example: Added depends_on with condition: service_healthy to docker-compose.yml
Impact: Now always wait for dependencies before starting, prevents flaky startup failures
        """.strip()
    },

    MemoryType.CONTEXT: {
        "required_fields": [],
        "suggested_structure": """
Context: [Important project/environment information]
Why Important: [Implications of this context]
Related: [What this affects]
        """.strip(),
        "example": """
Context: Enduro project uses PostgreSQL triggers for automatic balance calculations in cash wallet system
Why Important: Direct SQL updates bypass triggers, causing balance inconsistencies
Related: All wallet operations must use ORM methods, not raw SQL UPDATE statements
        """.strip()
    }
}


def get_template_hints(memory_type: MemoryType) -> dict:
    """Get template structure and examples for a memory type."""
    return MEMORY_TEMPLATES.get(memory_type, {})


def validate_against_template(memory: MemoryCreate) -> list[str]:
    """
    Check if memory follows best-practice template.
    Returns list of suggestions for improvement.
    """
    template = MEMORY_TEMPLATES.get(memory.type)
    if not template:
        return []

    suggestions = []

    # Check required fields
    for field_desc in template.get("required_fields", []):
        if "OR" in field_desc:
            # Handle OR conditions (e.g., "solution OR prevention")
            fields = [f.strip() for f in field_desc.split("OR")]
            if not any(getattr(memory, f, None) for f in fields):
                suggestions.append(f"Missing: {field_desc}")
        else:
            field_name = field_desc.lower().replace(" ", "_")
            if not getattr(memory, field_name, None):
                suggestions.append(f"Missing: {field_desc}")

    # Provide example if template available
    if suggestions and "example" in template:
        example_hint = f"\n\nExample of a high-quality {memory.type.value} memory:\n{template['example']}"
        suggestions.append(example_hint)

    return suggestions


# ============================================================================
# Semantic Deduplication
# ============================================================================

def check_duplicate_before_store(
    new_memory: MemoryCreate,
    similarity_threshold: float = 0.88
) -> Optional[dict]:
    """
    Check if similar memory already exists using semantic search.

    Args:
        new_memory: Memory to check
        similarity_threshold: Minimum similarity score to consider duplicate (0.88 = very similar)

    Returns:
        dict with duplicate info if found, None otherwise
    """
    try:
        from .models import SearchQuery

        # Search for similar memories using semantic search
        query = SearchQuery(
            query=new_memory.content,
            type=new_memory.type,
            limit=5,
            min_score=0.7  # Initial filter
        )

        similar_results = collections.search_memories(
            query=query,
            search_mode="semantic"  # Pure semantic for deduplication
        )

        if not similar_results:
            return None

        # Check if any result is above threshold
        top_result = similar_results[0]
        if top_result.score >= similarity_threshold:
            existing = top_result.memory

            # Determine suggestion: merge if different, skip if identical
            content_match = new_memory.content.strip().lower() == existing.content.strip().lower()

            return {
                "duplicate_detected": True,
                "existing_id": existing.id,
                "existing_content": existing.content[:200] + "..." if len(existing.content) > 200 else existing.content,
                "existing_tags": existing.tags,
                "similarity_score": round(top_result.score, 3),
                "suggestion": "skip" if content_match else "merge",
                "message": (
                    f"Very similar {new_memory.type.value} memory already exists (similarity: {top_result.score:.1%}). "
                    "Consider updating existing memory instead of creating duplicate."
                )
            }

        return None

    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")
        return None


# ============================================================================
# Tag Suggestions from Similar Memories
# ============================================================================

def suggest_tags_from_similar(
    content: str,
    existing_tags: list[str],
    limit: int = 3
) -> list[str]:
    """
    Suggest additional tags based on similar memories.

    Uses vector similarity to find memories with related content,
    then extracts commonly used tags from those memories.

    Args:
        content: Memory content to analyze
        existing_tags: Tags already provided by user
        limit: Maximum number of suggestions to return

    Returns:
        List of suggested tag names
    """
    try:
        from .models import SearchQuery

        # Find similar memories
        query = SearchQuery(
            query=content,
            limit=10,
            min_score=0.7  # Reasonably similar
        )

        similar_results = collections.search_memories(
            query=query,
            search_mode="semantic"
        )

        if not similar_results:
            return []

        # Count tag frequency in similar memories
        tag_frequency = defaultdict(int)
        for result in similar_results:
            for tag in result.memory.tags or []:
                # Skip tags user already provided
                if tag.lower() not in [t.lower() for t in existing_tags]:
                    # Weight by similarity score
                    tag_frequency[tag] += result.score

        # Sort by frequency (weighted by similarity)
        suggested = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [tag for tag, _ in suggested]

    except Exception as e:
        logger.warning(f"Tag suggestion failed: {e}")
        return []


# ============================================================================
# Rich Metadata Extraction
# ============================================================================

def extract_metadata(content: str) -> dict:
    """
    Extract structured metadata from memory content.

    Returns dict with:
    - technologies: List of detected tech stack items
    - file_paths: List of file paths mentioned
    - urls: List of URLs mentioned
    - code_snippets: Number of code blocks detected
    """
    import re

    metadata = {
        "technologies": [],
        "file_paths": [],
        "urls": [],
        "code_snippets": 0
    }

    # Extract URLs
    url_pattern = r'https?://[^\s<>"\']+'
    metadata["urls"] = re.findall(url_pattern, content)

    # Extract file paths (Unix/Windows style)
    path_pattern = r'(?:/[\w\-./]+|[A-Z]:\\[\w\-\\./]+|\.[\w\-./]+)'
    potential_paths = re.findall(path_pattern, content)
    # Filter to likely file paths (contain extension or common dirs)
    metadata["file_paths"] = [
        p for p in potential_paths
        if '.' in p or any(d in p for d in ['/src/', '/tests/', '/config/', '/docs/'])
    ]

    # Count code snippets (backticks, indented blocks)
    metadata["code_snippets"] = content.count('```') // 2  # Pairs of code fences

    # Extract common technologies (basic keyword matching)
    tech_keywords = {
        'python', 'javascript', 'typescript', 'java', 'rust', 'go', 'ruby',
        'react', 'vue', 'angular', 'svelte', 'django', 'flask', 'fastapi',
        'postgresql', 'mysql', 'mongodb', 'redis', 'neo4j', 'qdrant',
        'docker', 'kubernetes', 'aws', 'gcp', 'azure',
        'git', 'github', 'gitlab', 'ci/cd', 'nginx', 'apache'
    }

    content_lower = content.lower()
    for tech in tech_keywords:
        if tech in content_lower:
            metadata["technologies"].append(tech)

    return metadata


# ============================================================================
# Tag Normalization
# ============================================================================

def normalize_tags(tags: list[str] | None) -> list[str]:
    """Normalize tags: lowercase, strip, deduplicate, remove junk.

    Rules:
    - Lowercase all tags
    - Strip whitespace
    - Remove empty/blank tags and tags shorter than 2 chars
    - Deduplicate (preserving order)
    - Cap at 15 tags max
    """
    if not tags:
        return []

    seen: set[str] = set()
    normalized: list[str] = []

    for tag in tags:
        t = tag.strip().lower()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        normalized.append(t)

    return normalized[:15]


# ============================================================================
# Project Name Normalization
# ============================================================================

# Canonical project names: maps known aliases/variants → canonical slug
PROJECT_ALIASES: dict[str, str] = {
    # Claude Brain Memory System
    "claude brain memory system": "claude-brain",
    "claude brain": "claude-brain",
    "claude-brain-memory": "claude-brain",
    "claude_brain": "claude-brain",
    ".claude": "claude-brain",
    # Voice2type
    "voice2type": "voice2type",
    "Voice2type": "voice2type",
    # Enduro
    "enduro": "enduro-compta",
    "enduro-compta": "enduro-compta",
}


def normalize_project(project: str | None) -> str | None:
    """Normalize project name to canonical slug.

    Uses PROJECT_ALIASES for known projects, otherwise lowercases
    and converts spaces/underscores to hyphens for consistency.

    Returns None if project is None or empty.
    """
    if not project:
        return project

    stripped = project.strip()
    if not stripped:
        return None

    # Check exact match first (case-insensitive)
    lookup = stripped.lower()
    if lookup in PROJECT_ALIASES:
        return PROJECT_ALIASES[lookup]

    # Normalize: lowercase, spaces/underscores → hyphens, strip trailing hyphens
    import re
    normalized = re.sub(r'[\s_]+', '-', stripped.lower()).strip('-')

    # Check again after normalization
    if normalized in PROJECT_ALIASES:
        return PROJECT_ALIASES[normalized]

    return normalized


# ============================================================================
# Content Cleaning
# ============================================================================

def clean_content(content: str) -> str:
    """Clean memory content: normalize Unicode, strip control chars, collapse whitespace.

    Pipeline:
    1. Unicode NFC normalization (canonical decomposition → canonical composition)
    2. Remove control characters and zero-width spaces (keep newlines/tabs)
    3. Strip leading/trailing whitespace
    4. Collapse 3+ consecutive newlines to 2
    5. Collapse multiple consecutive spaces to single space (within lines)
    """
    # 1. Unicode NFC normalization
    content = unicodedata.normalize("NFC", content)

    # 2. Remove control chars (C0/C1) except \n \r \t, and zero-width chars
    content = _re_module.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u200b\u200c\u200d\ufeff]', '', content)

    # 3. Strip
    content = content.strip()

    # 4. Collapse 3+ newlines to 2
    content = _re_module.sub(r'\n{3,}', '\n\n', content)

    # 5. Collapse multiple spaces to single (within lines, not across newlines)
    content = _re_module.sub(r'[^\S\n]+', ' ', content)

    return content


# ============================================================================
# Auto-Enrich Type-Specific Fields
# ============================================================================

def _derive_context(content: str, project: str | None, mem_type: MemoryType) -> str | None:
    """Generate context from content — first sentence + project scope."""
    import re as _re

    # Split into sentences
    sentences = _re.split(r'(?<=[.!?])\s+', content)
    first = next((s.strip() for s in sentences if len(s.strip()) > 20), None)
    if not first:
        return None

    prefix = f"While working on {project}: " if project else ""
    # Cap at 250 chars
    derived = f"{prefix}{first}"
    return derived[:250]


def _derive_prevention(content: str, solution: str) -> str | None:
    """Derive prevention advice from solution and content."""
    content_lower = content.lower()

    # Check if content already has prevention-like phrases
    prevention_phrases = ['to prevent', 'to avoid', 'next time', 'going forward', 'in future']
    for phrase in prevention_phrases:
        idx = content_lower.find(phrase)
        if idx >= 0:
            end = content.find('.', idx)
            if end > idx:
                return content[idx:end + 1].strip()

    # Derive from solution
    if solution and len(solution) > 10:
        return f"To prevent: {solution.rstrip('.')}. Verify this proactively."

    return None


def _derive_rationale(content: str) -> str | None:
    """Extract rationale from content using explanation keywords."""
    content_lower = content.lower()
    keywords = ['because ', 'since ', 'in order to ', 'so that ', 'the reason ']

    for kw in keywords:
        idx = content_lower.find(kw)
        if idx >= 0:
            # Take from keyword to end of sentence
            end = content.find('.', idx)
            if end > idx:
                extracted = content[idx:end + 1].strip()
            else:
                extracted = content[idx:idx + 300].strip()
            if len(extracted) > 15:
                return extracted[0].upper() + extracted[1:]

    return None


def _derive_alternatives(content: str) -> list[str] | None:
    """Extract alternatives mentioned in content."""
    content_lower = content.lower()
    keywords = ['instead of ', 'rather than ', 'compared to ', 'alternative', 'other option',
                'could have used ', 'considered ']

    for kw in keywords:
        idx = content_lower.find(kw)
        if idx >= 0:
            end = content.find('.', idx)
            if end > idx:
                alt = content[idx:end + 1].strip()
                if len(alt) > 10:
                    return [alt]

    return None


def auto_enrich_fields(memory: MemoryCreate) -> MemoryCreate:
    """Auto-fill missing type-specific and context fields from content analysis.

    Extracts structured fields from the main content when they weren't
    explicitly provided. This maximizes content_richness score without
    requiring callers to always fill every field.

    Pipeline:
    1. Derive context from content (all types)
    2. Derive prevention from solution (error type)
    3. Derive rationale from content (decision type)
    4. Derive alternatives from content (decision type)
    """
    content = memory.content.strip()

    # ─── Context (all types) ───
    if not memory.context:
        derived = _derive_context(content, memory.project, memory.type)
        if derived:
            memory.context = derived
            logger.info(f"Auto-derived context: {derived[:60]}...")

    # ─── Error: prevention from solution ───
    if memory.type == MemoryType.ERROR:
        if memory.solution and not memory.prevention:
            derived = _derive_prevention(content, memory.solution)
            if derived:
                memory.prevention = derived
                logger.info(f"Auto-derived prevention: {derived[:60]}...")

    # ─── Decision: rationale and alternatives ───
    if memory.type == MemoryType.DECISION:
        if not memory.rationale:
            derived = _derive_rationale(content)
            if derived:
                memory.rationale = derived
                logger.info(f"Auto-derived rationale: {derived[:60]}...")

        if not memory.alternatives:
            derived = _derive_alternatives(content)
            if derived:
                memory.alternatives = derived
                logger.info(f"Auto-derived alternatives: {derived}")

    return memory


# ============================================================================
# Auto-Enrich Tags
# ============================================================================

def auto_enrich_tags(memory: MemoryCreate) -> MemoryCreate:
    """Auto-enrich memory tags: normalize, suggest from similar, extract from content.

    Pipeline:
    1. Normalize existing tags
    2. If below MIN_TAGS, suggest from similar memories
    3. Extract technologies from content and add as tags
    4. Re-normalize final list
    """
    from .quality import MIN_TAGS

    # 1. Normalize existing
    memory.tags = normalize_tags(memory.tags)

    # 2. If below minimum, suggest from similar memories
    if len(memory.tags) < MIN_TAGS:
        suggested = suggest_tags_from_similar(
            content=memory.content,
            existing_tags=memory.tags,
            limit=MIN_TAGS - len(memory.tags)
        )
        if suggested:
            memory.tags.extend(suggested)
            logger.info(f"Auto-enriched tags with suggestions: {suggested}")

    # 3. Extract technologies from content
    metadata = extract_metadata(memory.content)
    existing_lower = {t.lower() for t in memory.tags}
    for tech in metadata.get("technologies", []):
        if tech.lower() not in existing_lower:
            memory.tags.append(tech)
            existing_lower.add(tech.lower())

    # 3b. Extract keyphrases via YAKE and use as tag candidates
    if len(memory.tags) < 8:  # don't over-tag
        keyphrases = extract_keyphrases(memory.content, top_n=5)
        for kp in keyphrases:
            # Only use short keyphrases (1-2 words) as tags
            words = kp.split()
            if len(words) <= 2:
                tag_candidate = kp.lower().strip()
                if len(tag_candidate) >= 3 and tag_candidate not in existing_lower:
                    memory.tags.append(tag_candidate)
                    existing_lower.add(tag_candidate)

    # 4. Fallback: use memory type and project as tags if still below minimum
    if len(memory.tags) < MIN_TAGS:
        existing_lower = {t.lower() for t in memory.tags}
        fallbacks = [memory.type.value]
        if memory.project:
            fallbacks.append(memory.project)
        for fb in fallbacks:
            if fb.lower() not in existing_lower and len(fb) >= 2:
                memory.tags.append(fb.lower())
                existing_lower.add(fb.lower())
            if len(memory.tags) >= MIN_TAGS:
                break

    # 5. Re-normalize (dedup, cap)
    memory.tags = normalize_tags(memory.tags)

    return memory


# ============================================================================
# Enriched Embedding Text Builder
# ============================================================================

def build_embedding_text(memory) -> str:
    """Build an enriched text representation for embedding generation.

    Combines ALL available memory fields into a structured text that
    produces richer, more semantically precise embeddings. The same
    enrichment is already done at rerank time (reranker.py:96-113) —
    doing it here ensures embedding-time and rerank-time representations
    are consistent.

    Template per type:
    - ERROR:    [ERROR] Project: X. <content> Error: <msg> Solution: <sol> Prevention: <prev>
    - DECISION: [DECISION] Project: X. <content> Rationale: <rat> Alternatives: <alt>
    - PATTERN:  [PATTERN] Project: X. <content> Context: <ctx>
    - DOCS:     [DOCS] Project: X. <content> Source: <src>
    - LEARNING: [LEARNING] Project: X. <content>
    - CONTEXT:  [CONTEXT] Project: X. <content>

    All types append: Tags: <tag1, tag2, ...>
    """
    parts: list[str] = []

    # Type prefix for embedding disambiguation
    mem_type = memory.type.value if hasattr(memory.type, 'value') else str(memory.type)
    parts.append(f"[{mem_type.upper()}]")

    # Project scope
    if memory.project:
        parts.append(f"Project: {memory.project}.")

    # Main content (always present)
    parts.append(memory.content)

    # Context (universal enrichment)
    if memory.context:
        parts.append(f"Context: {memory.context}")

    # Type-specific fields
    if mem_type == "error":
        if memory.error_message:
            parts.append(f"Error: {memory.error_message}")
        if memory.solution:
            parts.append(f"Solution: {memory.solution}")
        if memory.prevention:
            parts.append(f"Prevention: {memory.prevention}")
    elif mem_type == "decision":
        if memory.rationale:
            parts.append(f"Rationale: {memory.rationale}")
        if memory.alternatives:
            alts = ", ".join(memory.alternatives) if isinstance(memory.alternatives, list) else str(memory.alternatives)
            parts.append(f"Alternatives: {alts}")
    elif mem_type == "docs":
        if getattr(memory, 'source', None):
            parts.append(f"Source: {memory.source}")

    # Tags as semantic hints (helps embed topical intent)
    if memory.tags:
        tag_list = memory.tags if isinstance(memory.tags, list) else [memory.tags]
        parts.append(f"Topics: {', '.join(tag_list)}.")

    return " ".join(parts)


def build_composite_embedding(memory, embed_fn) -> list[float]:
    """Generate weighted composite embedding from separate field groups.

    Weights: content 0.70, keyphrases 0.25, metadata 0.05
    Each group is embedded separately, then combined as weighted sum.
    Falls back to single embedding if keyphrases are empty.

    Args:
        memory: Memory object with content, tags, type, project fields
        embed_fn: Callable that takes (text) and returns {"dense": list[float], ...}
    """
    import numpy as np

    # Group 1: Main content (type prefix + content + context + type-specific fields)
    content_text = build_embedding_text(memory)
    content_emb = np.array(embed_fn(content_text)["dense"])

    # Group 2: Keyphrases (extracted or from tags)
    keyphrases = extract_keyphrases(memory.content, top_n=8)
    if not keyphrases and memory.tags:
        keyphrases = memory.tags[:5]

    if keyphrases:
        kp_text = " ".join(keyphrases)
        kp_emb = np.array(embed_fn(kp_text)["dense"])

        # Group 3: Metadata (project + type + tags as short text)
        meta_parts = [memory.type.value if hasattr(memory.type, 'value') else str(memory.type)]
        if memory.project:
            meta_parts.append(memory.project)
        meta_text = " ".join(meta_parts)
        meta_emb = np.array(embed_fn(meta_text)["dense"])

        # Weighted sum
        composite = 0.70 * content_emb + 0.25 * kp_emb + 0.05 * meta_emb
        # L2 normalize
        norm = np.linalg.norm(composite)
        if norm > 0:
            composite = composite / norm
        return composite.tolist()

    # Fallback: just use content embedding
    return content_emb.tolist()
