"""Memory quality validation and scoring.

Enforces quality standards for memories to ensure they are:
- Complete (sufficient detail)
- Searchable (proper tags)
- Contextual (explain WHY, not just WHAT)
- Actionable (include solutions, rationales, etc.)

Enforcement mode defaults to STRICT — low-quality memories are rejected at store time.
"""

import os
import logging
from .models import MemoryCreate, MemoryType

logger = logging.getLogger(__name__)

# Configuration from environment — defaults to STRICT enforcement
QUALITY_ENFORCEMENT = os.getenv("MEMORY_QUALITY_ENFORCEMENT", "strict")  # strict|warn|off
MIN_QUALITY_SCORE = float(os.getenv("MEMORY_MIN_QUALITY_SCORE", "0.6"))
MIN_TAGS = int(os.getenv("MEMORY_MIN_TAGS", "3"))
MIN_CONTENT_LENGTH = int(os.getenv("MEMORY_MIN_CONTENT_LENGTH", "50"))
MIN_WORDS = int(os.getenv("MEMORY_MIN_WORDS", "10"))


class QualityValidationError(Exception):
    """Raised when memory quality is too low."""
    def __init__(self, score: float, warnings: list[str]):
        self.score = score
        self.warnings = warnings
        message = f"Memory quality too low ({score:.2f}/1.0). Issues:\n" + "\n".join(f"  - {w}" for w in warnings)
        super().__init__(message)


def calculate_quality_score(memory: MemoryCreate) -> tuple[float, list[str]]:
    """
    Calculate quality score (0.0-1.0) at capture time.

    A well-formed memory with all required fields scores 1.0.
    Each missing or weak element reduces the score.
    The Pydantic validators catch hard failures; this catches soft quality issues.
    """
    score = 1.0
    warnings = []

    content = memory.content.strip()
    word_count = len(content.split())
    tag_count = len(memory.tags) if memory.tags else 0

    # ===== CONTENT QUALITY =====

    if len(content) < MIN_CONTENT_LENGTH:
        score -= 0.25
        warnings.append(f"Content too short ({len(content)} chars, need {MIN_CONTENT_LENGTH}+)")

    if word_count < MIN_WORDS:
        score -= 0.20
        warnings.append(f"Only {word_count} words (need {MIN_WORDS}+)")

    # Bonus tiers for rich content
    if len(content) < 100:
        score -= 0.05
        warnings.append("Content under 100 chars — consider adding more detail")
    elif len(content) >= 200:
        pass  # Good length, no penalty

    # Vague content detection — proportional to content length
    vague_phrases = ['fixed', 'updated', 'done', 'working', 'resolved', 'completed', 'finished']
    content_lower = content.lower()
    vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
    if vague_count > 0 and len(content) < 100:
        # Short + any vague phrase → strong penalty
        score -= 0.15
        warnings.append("Content seems vague — explain HOW and WHY, not just WHAT")
    elif vague_count >= 3 and len(content) < 300:
        # Medium-length but saturated with vague phrases → mild penalty
        score -= 0.05
        warnings.append("Content has multiple vague phrases — add specifics about approach and outcome")

    # Auto-captured boilerplate detection — heavily penalize machine-generated noise
    # Exempt session lifecycle memories (session-start/session-end) since they
    # serve session tracking on the Sessions page, not knowledge storage.
    tag_set = {t.lower() for t in memory.tags} if memory.tags else set()
    is_auto_captured = 'auto-captured' in tag_set
    is_session_lifecycle = 'session-start' in tag_set or 'session-end' in tag_set
    if is_auto_captured and not is_session_lifecycle:
        boilerplate_patterns = [
            'session started for project',
            'session closed at',
            'session ended at',
            'session resumed for project',
            'uncommitted files',
            'on branch main with',
            'on branch master with',
        ]
        if any(bp in content_lower for bp in boilerplate_patterns):
            score -= 0.40
            warnings.append("Content is auto-captured boilerplate — not a genuine memory")

    # ===== INFORMATION DENSITY =====

    words = content.split()
    if word_count >= 10:
        unique_words = set(w.lower() for w in words)
        density = len(unique_words) / word_count
        if density < 0.30:
            score -= 0.10
            warnings.append(f"Low information density ({density:.0%} unique words) — too much repetition")
        elif density < 0.40:
            score -= 0.05
            warnings.append(f"Moderate information density ({density:.0%} unique words) — consider adding more specific detail")

    # ===== TAG QUALITY =====

    if tag_count < MIN_TAGS:
        score -= 0.15
        warnings.append(f"Only {tag_count} tags (need {MIN_TAGS}+ for searchability)")

    if memory.tags:
        useless_tags = {'test', 'todo', 'temp', 'misc', 'other', 'general', 'stuff', 'code', 'fix', 'bug', 'update', 'auto-captured', 'session-start', 'session-end'}
        useful = [t for t in memory.tags if t.lower() not in useless_tags]
        if len(useful) < 2:
            score -= 0.15
            warnings.append("Too many generic tags — use specific, descriptive tags")

    # ===== PROJECT FIELD =====

    if not memory.project:
        score -= 0.05
        warnings.append("No project specified — add project for better organization")

    # ===== CONTEXT FIELD (universal quality signal) =====

    if not memory.context:
        if memory.type in (MemoryType.ERROR, MemoryType.DECISION, MemoryType.PATTERN):
            score -= 0.15
            warnings.append(f"Missing context — explain the situation that led to this {memory.type.value}")
        elif memory.type in (MemoryType.LEARNING, MemoryType.DOCS, MemoryType.CONTEXT):
            score -= 0.05
            warnings.append("Consider adding context for better future retrieval")

    # ===== TYPE-SPECIFIC COMPLETENESS =====

    if memory.type == MemoryType.ERROR:
        if not memory.error_message:
            score -= 0.15
            warnings.append("Missing error_message — include the actual error text")
        if not memory.solution:
            score -= 0.15
            warnings.append("Missing solution — explain how it was fixed")
        if not memory.prevention:
            score -= 0.10
            warnings.append("Missing prevention — explain how to avoid this in future")

    elif memory.type == MemoryType.DECISION:
        if not memory.rationale:
            score -= 0.20
            warnings.append("Missing rationale — explain WHY this was chosen")
        if not memory.alternatives:
            score -= 0.10
            warnings.append("Missing alternatives — list options that were considered")

    elif memory.type == MemoryType.PATTERN:
        if len(content) < 100:
            score -= 0.10
            warnings.append("Pattern too short — need 100+ chars to be reusable")

    elif memory.type == MemoryType.DOCS:
        if not memory.source:
            score -= 0.10
            warnings.append("Missing source URL or reference")

    # ===== FIELD SUBSTANCE (penalize trivially short type-specific fields) =====

    if memory.type == MemoryType.ERROR:
        if memory.solution and len(memory.solution.strip()) < 15:
            score -= 0.10
            warnings.append(f"Solution too brief ({len(memory.solution.strip())} chars) — explain the actual fix")
        if memory.prevention and len(memory.prevention.strip()) < 15:
            score -= 0.05
            warnings.append(f"Prevention too brief ({len(memory.prevention.strip())} chars) — explain how to avoid this")
        if memory.error_message and len(memory.error_message.strip()) < 10:
            score -= 0.05
            warnings.append(f"Error message too brief ({len(memory.error_message.strip())} chars) — include the actual error text")

    elif memory.type == MemoryType.DECISION:
        if memory.rationale and len(memory.rationale.strip()) < 15:
            score -= 0.10
            warnings.append(f"Rationale too brief ({len(memory.rationale.strip())} chars) — explain WHY this was chosen")

    # ===== SPECIFICITY BONUS (reward concrete, actionable content) =====

    import re
    specificity_signals = 0
    # Numbers / versions (e.g., "3.11", "768", "0.92")
    if re.search(r'\b\d+\.?\d*\b', content):
        specificity_signals += 1
    # File paths
    if re.search(r'[/\\][\w\-./\\]+\.\w+', content):
        specificity_signals += 1
    # Code-like content (function calls, imports, variable names)
    if re.search(r'\b\w+\.\w+\(', content) or '```' in content or 'import ' in content:
        specificity_signals += 1
    # Error messages / stack traces
    if re.search(r'(Error|Exception|Traceback|FATAL|Failed):', content):
        specificity_signals += 1

    if specificity_signals >= 3:
        score += 0.05  # Small bonus for highly specific content

    return max(0.0, min(1.0, round(score, 2))), warnings


def validate_memory_quality(memory: MemoryCreate) -> tuple[bool, float, list[str]]:
    """
    Validate memory quality and enforce standards.

    Default mode is STRICT: rejects memories below MIN_QUALITY_SCORE.
    This ensures only high-quality memories enter the database.
    """
    score, warnings = calculate_quality_score(memory)
    is_valid = score >= MIN_QUALITY_SCORE

    if warnings:
        log_level = logging.WARNING if not is_valid else logging.INFO
        logger.log(log_level, f"Memory quality score: {score:.2f}/1.0 (type={memory.type.value})")
        for warning in warnings:
            logger.log(log_level, f"  - {warning}")

    if QUALITY_ENFORCEMENT == "off":
        return True, score, warnings

    elif QUALITY_ENFORCEMENT == "warn":
        if not is_valid:
            logger.warning(f"LOW QUALITY MEMORY (allowed in warn mode): score={score:.2f}")
        return True, score, warnings

    elif QUALITY_ENFORCEMENT == "strict":
        if not is_valid:
            raise QualityValidationError(score, warnings)
        return True, score, warnings

    else:
        logger.error(f"Unknown MEMORY_QUALITY_ENFORCEMENT mode: {QUALITY_ENFORCEMENT}")
        return True, score, warnings


def get_quality_suggestions(memory_type: MemoryType) -> str:
    """Get quality suggestions for a specific memory type."""

    suggestions = {
        MemoryType.ERROR: """
To store an ERROR memory, you MUST provide:
  - content: Detailed description (50+ chars, 10+ words)
  - error_message: The actual error text
  - solution: How you fixed it
  - prevention: How to avoid it in future
  - context: What you were working on when this happened
  - tags: 3+ specific tags (e.g., ['python', 'fastapi', 'import-error'])
  - project: Project name
        """,

        MemoryType.DECISION: """
To store a DECISION memory, you MUST provide:
  - content: What was decided and its impact (50+ chars, 10+ words)
  - rationale: WHY this option was chosen
  - alternatives: List of other options considered
  - context: The situation/requirements that drove this decision
  - tags: 3+ specific tags (e.g., ['architecture', 'database', 'postgresql'])
  - project: Project name
        """,

        MemoryType.PATTERN: """
To store a PATTERN memory, you MUST provide:
  - content: Detailed pattern description (100+ chars)
  - context: When and where to apply this pattern
  - tags: 3+ specific tags (e.g., ['caching', 'redis', 'ttl-pattern'])
  - project: Project name
        """,

        MemoryType.DOCS: """
To store a DOCS memory, you MUST provide:
  - content: Key points summarized (50+ chars, 10+ words)
  - source: URL or reference
  - tags: 3+ specific tags (e.g., ['qdrant', 'api', 'filtering'])
  - project: Project name
        """,

        MemoryType.LEARNING: """
To store a LEARNING memory, you MUST provide:
  - content: What you learned and why it matters (50+ chars, 10+ words)
  - context: Why this was surprising or useful (recommended)
  - tags: 3+ specific tags (e.g., ['python', 'asyncio', 'event-loop'])
  - project: Project name
        """,

        MemoryType.CONTEXT: """
To store a CONTEXT memory, you MUST provide:
  - content: Important project context (50+ chars, 10+ words)
  - tags: 3+ specific tags (e.g., ['infrastructure', 'docker', 'production'])
  - project: Project name
        """
    }

    return suggestions.get(memory_type, "Add detail, context, and 3+ descriptive tags.")
