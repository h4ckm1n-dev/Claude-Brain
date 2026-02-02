"""Pydantic models for the Advanced Memory Service API.

Supports:
- Multi-tier memory (episodic, semantic, procedural)
- Importance scoring with recency decay
- Archival and consolidation
- Hybrid search modes
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo
from uuid6 import uuid7


def utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class MemoryType(str, Enum):
    """Types of memories that can be stored."""
    ERROR = "error"
    DOCS = "docs"
    DECISION = "decision"
    PATTERN = "pattern"
    LEARNING = "learning"
    CONTEXT = "context"


class MemoryTier(str, Enum):
    """Memory storage tiers for lifecycle management."""
    EPISODIC = "episodic"    # Recent, raw interactions (short-term)
    SEMANTIC = "semantic"     # Consolidated knowledge (long-term)
    PROCEDURAL = "procedural" # Workflows and routines (permanent)


class RelationType(str, Enum):
    """Types of relationships between memories."""
    CAUSES = "causes"
    FIXES = "fixes"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    FOLLOWS = "follows"
    RELATED = "related"
    SUPERSEDES = "supersedes"  # For decisions that replace older ones
    SIMILAR_TO = "similar_to"  # For deduplication linking


class ChangeType(str, Enum):
    """Types of changes that create new versions."""
    CREATED = "created"
    EDITED = "edited"
    CONSOLIDATED = "consolidated"
    RECONSOLIDATED = "reconsolidated"
    RESTORED = "restored"


class Relation(BaseModel):
    """A relationship between two memories."""
    target_id: str
    relation_type: RelationType
    created_at: datetime = Field(default_factory=utc_now)


class MemoryVersion(BaseModel):
    """A single version snapshot of a memory."""
    version_number: int
    content: str
    importance_score: float
    tags: list[str]
    created_at: datetime
    change_type: ChangeType
    change_reason: Optional[str] = None
    changed_by: Literal["system", "user"] = "system"

    # Type-specific fields that might change
    error_message: Optional[str] = None
    solution: Optional[str] = None
    decision: Optional[str] = None
    rationale: Optional[str] = None


class MemoryBase(BaseModel):
    """Base memory model with common fields."""
    type: MemoryType
    content: str
    tags: list[str] = Field(default_factory=list)
    project: Optional[str] = None
    source: Optional[str] = None
    context: Optional[str] = None


class MemoryCreate(MemoryBase):
    """Model for creating a new memory with quality validation."""
    # Error-specific fields
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    solution: Optional[str] = None
    prevention: Optional[str] = None

    # Decision-specific fields
    decision: Optional[str] = None
    rationale: Optional[str] = None
    alternatives: Optional[list[str]] = None
    reversible: Optional[bool] = None
    impact: Optional[str] = None

    # Optional tier specification (defaults to episodic)
    memory_tier: MemoryTier = MemoryTier.EPISODIC

    # Session tracking (Phase 1.3)
    session_id: Optional[str] = None
    conversation_context: Optional[str] = None
    session_sequence: Optional[int] = None

    @field_validator('content')
    @classmethod
    def validate_content_quality(cls, v: str) -> str:
        """Enforce minimum content quality standards."""
        content = v.strip()

        # Minimum length check
        if len(content) < 30:
            raise ValueError(f"Content too short ({len(content)} chars). Minimum 30 characters required for searchability and usefulness.")

        # Minimum word count
        word_count = len(content.split())
        if word_count < 5:
            raise ValueError(f"Content has only {word_count} words. Minimum 5 words required. Avoid placeholders like 'test', 'todo', 'tbd'.")

        # Reject placeholder content
        if content.lower() in ['test', 'todo', 'placeholder', 'tbd', 'fixme', 'xxx']:
            raise ValueError(f"Content '{content}' is a placeholder. Provide actual information.")

        return content

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Enforce minimum tag requirements for searchability."""
        if len(v) < 2:
            raise ValueError(f"Only {len(v)} tags provided. Minimum 2 descriptive tags required for searchability. Examples: ['python', 'error'], ['decision', 'architecture', 'database']")

        # Check for useless tags
        useless_tags = {'test', 'todo', 'temp', 'misc', 'other', 'general', 'stuff'}
        if all(tag.lower() in useless_tags for tag in v):
            raise ValueError(f"All tags are generic ({v}). Use specific, descriptive tags related to the content.")

        return v

    @model_validator(mode='after')
    def validate_type_specific_requirements(self) -> 'MemoryCreate':
        """Validate type-specific requirements after all fields are set."""

        # DECISION memories must have rationale
        if self.type == MemoryType.DECISION:
            if not self.rationale:
                raise ValueError(
                    "Decision memories must include 'rationale' field explaining WHY this decision was made. "
                    "What problem does it solve? What are the benefits? "
                    "Example: rationale='Need ACID compliance for transactions, strong JSON support'"
                )

        # ERROR memories must have solution OR prevention
        if self.type == MemoryType.ERROR:
            if not self.solution and not self.prevention:
                raise ValueError(
                    "Error memories must include either 'solution' (how it was fixed) or 'prevention' (how to avoid it). "
                    "This makes the memory actionable for future reference. "
                    "Example: solution='Upgrade package to v3.0.0' or prevention='Pin version in requirements.txt'"
                )

        return self


class Memory(MemoryBase):
    """Full memory model with all fields."""
    id: str = Field(default_factory=lambda: str(uuid7()))
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_accessed: datetime = Field(default_factory=utc_now)

    # Lifecycle management
    memory_tier: MemoryTier = MemoryTier.EPISODIC
    archived: bool = False
    archived_at: Optional[datetime] = None

    # Scoring
    access_count: int = 0
    usefulness_score: float = 0.5
    importance_score: float = 0.5  # Heuristic-based importance
    recency_score: float = 1.0     # Decays over time
    pinned: bool = False           # Pinned memories never decay

    # Adaptive forgetting (FadeMem-inspired)
    memory_strength: float = 1.0   # Strength from 0.0-1.0, starts at 1.0
    decay_rate: float = 0.005      # Differential decay rate (lower = slower decay)
    last_decay_update: datetime = Field(default_factory=utc_now)

    # Session-based memory extraction (Phase 1.3)
    session_id: Optional[str] = None           # Conversation session identifier
    conversation_context: Optional[str] = None  # Previous messages for context
    session_sequence: Optional[int] = None      # Order within session (0, 1, 2, ...)

    # User Quality Ratings
    user_rating: Optional[float] = None  # Running average of user ratings (1-5 stars)
    user_rating_count: int = 0           # Number of ratings received
    user_feedback: Optional[list[dict]] = None  # List of {rating, feedback, timestamp}

    # Status
    resolved: bool = False
    relations: list[Relation] = Field(default_factory=list)

    # Error-specific fields
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    solution: Optional[str] = None
    prevention: Optional[str] = None

    # Decision-specific fields
    decision: Optional[str] = None
    rationale: Optional[str] = None
    alternatives: Optional[list[str]] = None
    reversible: Optional[bool] = None
    impact: Optional[str] = None

    # Consolidation tracking
    consolidated_from: Optional[list[str]] = None  # IDs of source memories
    consolidation_summary: Optional[str] = None

    # Version history
    current_version: int = 1
    version_history: list[MemoryVersion] = Field(default_factory=list)

    class Config:
        from_attributes = True

    def create_version_snapshot(
        self,
        change_type: ChangeType,
        change_reason: Optional[str] = None,
        changed_by: Literal["system", "user"] = "system"
    ) -> MemoryVersion:
        """
        Create a version snapshot before modifying memory.

        Returns the created version for potential storage.
        """
        snapshot = MemoryVersion(
            version_number=self.current_version,
            content=self.content,
            importance_score=self.importance_score,
            tags=self.tags.copy() if self.tags else [],
            created_at=utc_now(),
            change_type=change_type,
            change_reason=change_reason,
            changed_by=changed_by,
            error_message=self.error_message,
            solution=self.solution,
            decision=self.decision,
            rationale=self.rationale
        )

        self.version_history.append(snapshot)
        self.current_version += 1

        return snapshot

    def calculate_importance(self) -> float:
        """Calculate importance score based on heuristics."""
        score = 0.5  # Base score

        # Type-based importance
        type_weights = {
            MemoryType.ERROR: 0.8,
            MemoryType.DECISION: 0.9,
            MemoryType.PATTERN: 0.7,
            MemoryType.DOCS: 0.5,
            MemoryType.LEARNING: 0.6,
            MemoryType.CONTEXT: 0.4,
        }
        score = type_weights.get(self.type, 0.5)

        # Boost for tags (more tags = more specific)
        score += min(len(self.tags) * 0.05, 0.2)

        # Boost for content length (detailed = more valuable)
        if len(self.content) > 500:
            score += 0.1

        # Boost for having solution (for errors)
        if self.solution:
            score += 0.15

        # Boost for being in semantic/procedural tier
        if self.memory_tier == MemoryTier.SEMANTIC:
            score += 0.1
        elif self.memory_tier == MemoryTier.PROCEDURAL:
            score += 0.15

        return min(score, 1.0)

    def calculate_recency(self, decay_rate: float = 0.005) -> float:
        """
        Calculate recency score with exponential decay.
        decay_rate=0.005 gives ~6 day half-life
        """
        import math
        hours_old = (utc_now() - self.created_at).total_seconds() / 3600
        return math.exp(-decay_rate * hours_old)

    def composite_score(self, relevance: float = 1.0) -> float:
        """
        Calculate composite score for ranking with memory strength.
        score = (importance * 0.3) + (relevance * 0.35) + (recency * 0.2) + (strength * 0.15)
        """
        importance = self.calculate_importance()
        recency = self.calculate_recency()
        strength = self.memory_strength if hasattr(self, 'memory_strength') else 1.0
        return (importance * 0.3) + (relevance * 0.35) + (recency * 0.2) + (strength * 0.15)

    def calculate_decay_rate(self) -> float:
        """
        Calculate differential decay rate based on importance and semantic relevance.
        High-importance memories decay slower (lower decay_rate).

        Returns:
            float: Decay rate (0.001 to 0.01), where lower = slower decay
        """
        import math

        # Base decay rate
        base_rate = 0.005

        # Importance factor: higher importance = lower decay
        importance = self.calculate_importance()
        importance_factor = 1.0 - (importance * 0.7)  # Range: 0.3 to 1.0

        # Access frequency factor: frequently accessed = lower decay
        # Normalize access_count (assume max ~50 accesses is very frequent)
        access_frequency = min(self.access_count / 50.0, 1.0)
        access_factor = 1.0 - (access_frequency * 0.5)  # Range: 0.5 to 1.0

        # Memory tier factor: procedural < semantic < episodic decay
        tier_factors = {
            MemoryTier.PROCEDURAL: 0.3,  # Slowest decay
            MemoryTier.SEMANTIC: 0.6,
            MemoryTier.EPISODIC: 1.0     # Fastest decay
        }
        tier_factor = tier_factors.get(self.memory_tier, 1.0)

        # Combined decay rate
        decay_rate = base_rate * importance_factor * access_factor * tier_factor

        # Clamp to reasonable bounds
        return max(0.001, min(decay_rate, 0.01))

    def calculate_memory_strength(self, time_elapsed_hours: Optional[float] = None) -> float:
        """
        Calculate current memory strength with exponential decay.
        Formula: strength(t) = initial_strength * exp(-decay_rate * time_elapsed)

        Args:
            time_elapsed_hours: Hours since last decay update. If None, calculates from last_decay_update.

        Returns:
            float: Memory strength (0.0-1.0)
        """
        import math

        # Pinned memories never decay
        if self.pinned:
            return 1.0

        # Calculate time elapsed
        if time_elapsed_hours is None:
            now = utc_now()
            last_update = self.last_decay_update
            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)
            time_elapsed_hours = (now - last_update).total_seconds() / 3600

        # Get current strength (default to 1.0 for old memories)
        current_strength = getattr(self, 'memory_strength', 1.0)

        # Get decay rate (recalculate to account for changing factors)
        decay_rate = self.calculate_decay_rate()

        # Apply exponential decay
        new_strength = current_strength * math.exp(-decay_rate * time_elapsed_hours)

        # Clamp to [0.0, 1.0]
        return max(0.0, min(new_strength, 1.0))


class MemoryUpdate(BaseModel):
    """Model for updating an existing memory."""
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    solution: Optional[str] = None
    prevention: Optional[str] = None
    resolved: Optional[bool] = None
    usefulness_score: Optional[float] = None
    importance_score: Optional[float] = None
    memory_tier: Optional[MemoryTier] = None
    archived: Optional[bool] = None


# Search modes for hybrid search
SearchMode = Literal["semantic", "keyword", "hybrid"]


class SearchQuery(BaseModel):
    """Model for semantic search queries."""
    query: str
    type: Optional[MemoryType] = None
    tags: Optional[list[str]] = None
    project: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)

    # Advanced search options
    search_mode: SearchMode = "hybrid"
    include_archived: bool = False
    memory_tier: Optional[MemoryTier] = None
    importance_threshold: Optional[float] = None
    time_range_hours: Optional[int] = None


class SearchResult(BaseModel):
    """A single search result with score."""
    memory: Memory
    score: float
    composite_score: Optional[float] = None  # Combined importance/recency/relevance


class EmbedRequest(BaseModel):
    """Request to generate an embedding."""
    text: str
    include_sparse: bool = False


class EmbedResponse(BaseModel):
    """Response with generated embedding."""
    dense: list[float]
    sparse: Optional[dict] = None  # {indices: [], values: []}
    dimensions: int


class LinkRequest(BaseModel):
    """Request to link two memories."""
    source_id: str
    target_id: str
    relation_type: RelationType


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    qdrant: str
    collections: list[str]
    memory_count: int
    document_chunks: int = 0  # Number of document chunks indexed
    hybrid_search_enabled: bool = False
    graph_enabled: bool = False
    embedding_model: str = ""
    embedding_dim: int = 0


class StatsResponse(BaseModel):
    """Statistics response."""
    total_memories: int
    active_memories: int
    archived_memories: int
    by_type: dict[str, int]
    by_tier: dict[str, int] = Field(default_factory=dict)
    unresolved_errors: int
    hybrid_search_enabled: bool = False
    embedding_dim: int = 0


class ArchiveRequest(BaseModel):
    """Request to archive memories."""
    older_than_days: int = Field(default=7, ge=1)
    dry_run: bool = False
    min_access_count: int = Field(default=3, ge=0)


class ArchiveResult(BaseModel):
    """Result of archive operation."""
    analyzed: int
    consolidated: int
    archived: int
    deleted: int
    kept: int
    dry_run: bool
    details: Optional[dict] = None


class ConsolidationCluster(BaseModel):
    """A cluster of similar memories for consolidation."""
    memory_ids: list[str]
    similarity_score: float
    suggested_summary: Optional[str] = None
    suggested_type: MemoryType
    suggested_tags: list[str]


class MigrationResult(BaseModel):
    """Result of collection migration."""
    total: int
    migrated: int
    failed: int
    new_embedding_dim: int
    hybrid_search_enabled: bool
