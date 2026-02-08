"""Advanced memory quality enhancements.

Features:
- Semantic deduplication (prevent duplicate knowledge)
- Automatic tag suggestions from similar memories
- Template-based validation hints
"""

import logging
from typing import Optional
from collections import defaultdict

from .models import MemoryCreate, MemoryType
from . import collections
from .embeddings import embed_text

logger = logging.getLogger(__name__)


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
# Content Cleaning
# ============================================================================

def clean_content(content: str) -> str:
    """Clean memory content: strip, collapse excess whitespace/newlines.

    - Strip leading/trailing whitespace
    - Collapse 3+ consecutive newlines to 2
    - Collapse multiple consecutive spaces to single space (within lines)
    """
    import re

    content = content.strip()
    # Collapse 3+ newlines to 2
    content = re.sub(r'\n{3,}', '\n\n', content)
    # Collapse multiple spaces to single (within lines, not across newlines)
    content = re.sub(r'[^\S\n]+', ' ', content)
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
