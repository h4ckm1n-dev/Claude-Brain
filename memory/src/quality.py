"""Memory quality validation and scoring.

Enforces quality standards for memories to ensure they are:
- Complete (sufficient detail)
- Searchable (proper tags)
- Contextual (explain WHY, not just WHAT)
- Actionable (include solutions, rationales, etc.)
"""

import os
import logging
from .models import MemoryCreate, MemoryType

logger = logging.getLogger(__name__)

# Configuration from environment
QUALITY_ENFORCEMENT = os.getenv("MEMORY_QUALITY_ENFORCEMENT", "warn")  # strict|warn|off
MIN_QUALITY_SCORE = int(os.getenv("MEMORY_MIN_QUALITY_SCORE", "50"))
REQUIRE_CONTEXT_FOR_DECISIONS = os.getenv("MEMORY_REQUIRE_CONTEXT_FOR_DECISIONS", "true").lower() == "true"
REQUIRE_CONTEXT_FOR_PATTERNS = os.getenv("MEMORY_REQUIRE_CONTEXT_FOR_PATTERNS", "true").lower() == "true"
REQUIRE_CONTEXT_FOR_ERRORS = os.getenv("MEMORY_REQUIRE_CONTEXT_FOR_ERRORS", "true").lower() == "true"
MIN_TAGS = int(os.getenv("MEMORY_MIN_TAGS", "2"))
MIN_CONTENT_LENGTH = int(os.getenv("MEMORY_MIN_CONTENT_LENGTH", "30"))
MIN_WORDS = int(os.getenv("MEMORY_MIN_WORDS", "5"))


class QualityValidationError(Exception):
    """Raised when memory quality is too low."""
    def __init__(self, score: int, warnings: list[str]):
        self.score = score
        self.warnings = warnings
        message = f"Memory quality too low ({score}/100). Issues:\n" + "\n".join(f"  - {w}" for w in warnings)
        super().__init__(message)


def calculate_quality_score(memory: MemoryCreate) -> tuple[int, list[str]]:
    """
    Calculate quality score (0-100) and return warnings.

    Args:
        memory: Memory to validate

    Returns:
        tuple: (score, warnings)
    """
    score = 100
    warnings = []

    content = memory.content.strip()
    word_count = len(content.split())

    # ===== CRITICAL ISSUES (High penalty) =====

    # Minimum content length
    if len(content) < MIN_CONTENT_LENGTH:
        score -= 30
        warnings.append(f"Content too short ({len(content)} chars, need {MIN_CONTENT_LENGTH}+)")

    # Minimum word count
    if word_count < MIN_WORDS:
        score -= 25
        warnings.append(f"Content has only {word_count} words (need {MIN_WORDS}+)")

    # Placeholder/test content
    placeholder_phrases = {'test', 'todo', 'placeholder', 'tbd', 'fixme', 'xxx'}
    if content.lower() in placeholder_phrases:
        score -= 50
        warnings.append("Content is a placeholder - provide actual information")

    # Generic/useless tags
    if memory.tags:
        useless_tags = {'test', 'todo', 'temp', 'misc', 'other', 'general'}
        if all(tag.lower() in useless_tags for tag in memory.tags):
            score -= 30
            warnings.append("All tags are generic - use descriptive tags")

    # ===== IMPORTANT ISSUES (Medium penalty) =====

    # Tag count
    tag_count = len(memory.tags) if memory.tags else 0
    if tag_count < MIN_TAGS:
        score -= 20
        warnings.append(f"Only {tag_count} tags (need {MIN_TAGS}+ for searchability)")

    # Vague content (short + contains trigger words)
    vague_phrases = ['fixed', 'updated', 'done', 'working', 'resolved', 'completed', 'finished']
    content_lower = content.lower()
    has_vague_words = any(phrase in content_lower for phrase in vague_phrases)
    if has_vague_words and len(content) < 80:
        score -= 20
        warnings.append("Content seems vague - explain HOW and WHY, not just WHAT")

    # ===== TYPE-SPECIFIC VALIDATION =====

    # DECISION memories
    if memory.type == MemoryType.DECISION:
        if not memory.rationale:
            score -= 30
            warnings.append("Decision must include rationale explaining WHY this was chosen")

        if not memory.alternatives:
            score -= 10
            warnings.append("Decision should list alternatives that were considered")

        if REQUIRE_CONTEXT_FOR_DECISIONS and not memory.context:
            score -= 15
            warnings.append("Decision should include context explaining the situation")

    # ERROR memories
    elif memory.type == MemoryType.ERROR:
        if not memory.solution and not memory.prevention:
            score -= 25
            warnings.append("Error should include either solution (how it was fixed) or prevention (how to avoid)")

        if not memory.error_message:
            score -= 10
            warnings.append("Error should include the actual error message")

        if REQUIRE_CONTEXT_FOR_ERRORS and not memory.context:
            score -= 10
            warnings.append("Error should include context about when/why it occurred")

    # PATTERN memories
    elif memory.type == MemoryType.PATTERN:
        if REQUIRE_CONTEXT_FOR_PATTERNS and not memory.context:
            score -= 15
            warnings.append("Pattern should include context explaining when to use this pattern")

        if len(content) < 100:
            score -= 10
            warnings.append("Pattern should be detailed enough to be reusable (100+ chars)")

    # DOCS memories
    elif memory.type == MemoryType.DOCS:
        if not memory.source:
            score -= 5
            warnings.append("Docs should include source URL or reference")

    # ===== MINOR ISSUES (Low penalty) =====

    # No project specified (for project-specific knowledge)
    if not memory.project and memory.type in [MemoryType.DECISION, MemoryType.PATTERN]:
        score -= 5
        warnings.append("Consider adding project name for project-specific knowledge")

    # Short content for detailed types
    if memory.type in [MemoryType.DECISION, MemoryType.PATTERN] and len(content) < 50:
        score -= 10
        warnings.append(f"{memory.type.value} should be more detailed (50+ chars)")

    return max(0, score), warnings


def validate_memory_quality(memory: MemoryCreate) -> tuple[bool, int, list[str]]:
    """
    Validate memory quality and optionally raise exception.

    Args:
        memory: Memory to validate

    Returns:
        tuple: (is_valid, score, warnings)

    Raises:
        QualityValidationError: If enforcement is 'strict' and score < threshold
    """
    # Calculate quality score
    score, warnings = calculate_quality_score(memory)

    # Determine if valid
    is_valid = score >= MIN_QUALITY_SCORE

    # Log results
    if warnings:
        log_level = logging.WARNING if not is_valid else logging.INFO
        logger.log(log_level, f"Memory quality score: {score}/100 (type={memory.type.value})")
        for warning in warnings:
            logger.log(log_level, f"  - {warning}")

    # Handle enforcement modes
    if QUALITY_ENFORCEMENT == "off":
        # No enforcement, always allow
        return True, score, warnings

    elif QUALITY_ENFORCEMENT == "warn":
        # Warn but allow
        if not is_valid:
            logger.warning(f"LOW QUALITY MEMORY (but allowed): score={score}, threshold={MIN_QUALITY_SCORE}")
        return True, score, warnings

    elif QUALITY_ENFORCEMENT == "strict":
        # Block if below threshold
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
Quality tips for ERROR memories:
  - Include the actual error message
  - Explain what you were trying to do
  - Document the solution that worked
  - Add prevention advice for future
  - Use tags like: [error-type, technology, component]
        """,

        MemoryType.DECISION: """
Quality tips for DECISION memories:
  - Explain WHY this decision was made (rationale)
  - List alternatives that were considered
  - Add context about the situation/requirements
  - Mention trade-offs or impact
  - Use tags like: [decision-type, technology, architecture]
        """,

        MemoryType.PATTERN: """
Quality tips for PATTERN memories:
  - Describe the pattern in detail (100+ chars)
  - Explain when to use this pattern
  - Include code examples if applicable
  - Add context about benefits/trade-offs
  - Use tags like: [pattern-type, technology, use-case]
        """,

        MemoryType.DOCS: """
Quality tips for DOCS memories:
  - Include source URL or reference
  - Summarize key points (don't just copy)
  - Add context about when this is useful
  - Use specific tags (library version, etc.)
  - Use tags like: [library, version, topic]
        """,

        MemoryType.LEARNING: """
Quality tips for LEARNING memories:
  - Explain what you learned (not just what happened)
  - Add context about why this was surprising/useful
  - Include examples or scenarios
  - Use tags to categorize the learning
  - Use tags like: [technology, concept, insight]
        """,

        MemoryType.CONTEXT: """
Quality tips for CONTEXT memories:
  - Provide enough detail for future reference
  - Explain why this context is important
  - Add project name if project-specific
  - Use descriptive tags
  - Use tags like: [project, component, requirement]
        """
    }

    return suggestions.get(memory_type, "Add detail, context, and descriptive tags.")
