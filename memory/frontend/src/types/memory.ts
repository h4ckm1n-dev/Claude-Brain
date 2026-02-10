export enum MemoryType {
  ERROR = "error",
  DOCS = "docs",
  DECISION = "decision",
  PATTERN = "pattern",
  LEARNING = "learning",
  CONTEXT = "context",
}

export enum MemoryTier {
  EPISODIC = "episodic",
  SEMANTIC = "semantic",
  PROCEDURAL = "procedural",
}

export enum RelationType {
  CAUSES = "causes",
  FIXES = "fixes",
  CONTRADICTS = "contradicts",
  SUPPORTS = "supports",
  FOLLOWS = "follows",
  RELATED = "related",
  SUPERSEDES = "supersedes",
  SIMILAR_TO = "similar_to",
}

export interface Relation {
  target_id: string;
  relation_type: RelationType;
  created_at: string;
}

export interface Memory {
  id: string;
  type: MemoryType;
  content: string;
  tags: string[];
  project?: string;
  source?: string;
  context?: string;

  // Timestamps
  created_at: string;
  updated_at: string;
  last_accessed: string;

  // Lifecycle
  memory_tier: MemoryTier;
  archived: boolean;
  archived_at?: string;

  // Scoring
  access_count: number;
  usefulness_score: number;
  importance_score: number;
  recency_score: number;
  pinned: boolean;

  // Status
  resolved: boolean;
  relations: Relation[];

  // Type-specific fields
  error_message?: string;
  stack_trace?: string;
  solution?: string;
  prevention?: string;
  decision?: string;
  rationale?: string;
  alternatives?: string[];
  reversible?: boolean;
  impact?: string;

  // Consolidation
  consolidated_from?: string[];
  consolidation_summary?: string;
}

export interface PaginatedMemories {
  items: Memory[];
  total: number;
  limit: number;
  offset: number;
}

export interface MemoryCreate {
  type: MemoryType;
  content: string;
  tags?: string[];
  project?: string;
  source?: string;
  context?: string;
  memory_tier?: MemoryTier;

  // Type-specific
  error_message?: string;
  stack_trace?: string;
  solution?: string;
  prevention?: string;
  decision?: string;
  rationale?: string;
  alternatives?: string[];
  reversible?: boolean;
  impact?: string;
}

export interface SearchQuery {
  query: string;
  type?: MemoryType;
  tags?: string[];
  project?: string;
  limit?: number;
  min_score?: number;
  search_mode?: "semantic" | "keyword" | "hybrid";
  include_archived?: boolean;
  memory_tier?: MemoryTier;
  importance_threshold?: number;
  time_range_hours?: number;
}

export interface SearchResult {
  memory: Memory;
  score: number;
  composite_score?: number;
  memory_strength?: number;
}

export interface HealthResponse {
  status: string;
  qdrant: string;
  collections: string[];
  memory_count: number;
  hybrid_search_enabled: boolean;
  graph_enabled: boolean;
  embedding_model: string;
  embedding_dim: number;
}

export interface StatsResponse {
  total_memories: number;
  active_memories: number;
  archived_memories: number;
  by_type: Record<string, number>;
  by_tier: Record<string, number>;
  by_project?: Record<string, number>;
  unresolved_errors: number;
  hybrid_search_enabled: boolean;
  embedding_dim: number;
}

export interface GraphStats {
  enabled: boolean;
  memory_nodes: number;
  project_nodes: number;
  tag_nodes: number;
  relationships: number;
}

export interface SuggestionRequest {
  project?: string;
  keywords?: string[];
  current_files?: string[];
  git_branch?: string;
  limit?: number;
}

export interface Suggestion {
  id: string;
  type: MemoryType;
  content: string;
  reason: string;
  tags: string[];
  access_count: number;
  combined_score: number;
}

export interface ConsolidateRequest {
  older_than_days?: number;
  dry_run?: boolean;
}

export interface ConsolidationDetail {
  cluster_id: string;
  memory_ids: string[];
  action: string;
  reason: string;
}

export interface ConsolidateResult {
  analyzed: number;
  consolidated: number;
  archived: number;
  deleted: number;
  kept: number;
  dry_run: boolean;
  details?: ConsolidationDetail[];
}

// ============================================================================
// Phase 3-4: Quality Tracking Types
// ============================================================================

export interface QualityStats {
  // Actual backend fields
  total_count?: number;
  average_score?: number;
  min_score?: number;
  max_score?: number;
  distribution?: {
    excellent: number;
    good: number;
    moderate: number;
    low: number;
    poor: number;
  };
  // Expected frontend fields
  total_memories: number;
  avg_quality_score: number;
  quality_distribution: {
    excellent: number;  // 0.8-1.0
    good: number;       // 0.6-0.8
    fair: number;       // 0.4-0.6
    poor: number;       // 0.2-0.4
    very_poor: number;  // 0.0-0.2
  };
  high_quality_count?: number;
  promotion_eligible_count?: number;
  needs_improvement_count?: number;
}

export interface QualityTrend {
  memory_id: string;
  trend_data: Array<{
    timestamp: string;
    quality_score: number;
    reason: string;
  }>;
}

export interface PromotionCandidate {
  memory_id: string;
  current_state: string;
  quality_score: number;
  access_count: number;
  relationship_count: number;
  age_days: number;
  promotion_reason: string;
}

// ============================================================================
// Phase 3-4: Lifecycle State Machine Types
// ============================================================================

export enum MemoryState {
  EPISODIC = "episodic",
  STAGING = "staging",
  SEMANTIC = "semantic",
  PROCEDURAL = "procedural",
  ARCHIVED = "archived",
  PURGED = "purged",
}

export interface LifecycleStats {
  // Actual backend fields
  total?: number;
  distribution?: Record<string, number>;
  // Expected frontend fields
  total_memories: number;
  state_distribution: Record<MemoryState, number>;
  avg_time_in_episodic_hours?: number;
  avg_time_to_semantic_hours?: number;
  transition_flow?: Array<{
    from_state: MemoryState;
    to_state: MemoryState;
    count: number;
  }>;
}

export interface StateHistory {
  memory_id: string;
  transitions: Array<{
    timestamp: string;
    from_state: MemoryState;
    to_state: MemoryState;
    reason: string;
    actor: string;
  }>;
}

export interface StateTransition {
  memory_id: string;
  from_state: MemoryState;
  to_state: MemoryState;
  timestamp: string;
  reason: string;
  actor: string;
}

// ============================================================================
// Phase 3-4: Audit Trail Types
// ============================================================================

export enum AuditAction {
  CREATE = "create",
  UPDATE = "update",
  DELETE = "delete",
  ARCHIVE = "archive",
  RESOLVE = "resolve",
  PIN = "pin",
  UNPIN = "unpin",
  RATE = "rate",
  REINFORCE = "reinforce",
  STATE_TRANSITION = "state_transition",
  TIER_PROMOTION = "tier_promotion",
  QUALITY_UPDATE = "quality_update",
}

export interface AuditEntry {
  id: string;
  memory_id?: string;
  action: AuditAction;
  actor: string;
  timestamp: string;
  reason?: string;
  changes?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface AuditStats {
  total_entries: number;
  by_action: Record<AuditAction, number>;
  by_actor: Record<string, number>;
  activity_by_day: Array<{
    date: string;
    count: number;
  }>;
  recent_activity: AuditEntry[];
}

export interface MemoryVersion {
  version_id: string;
  memory_id: string;
  content: string;
  timestamp: string;
  actor: string;
  change_summary: string;
}

// ============================================================================
// Phase 3-4: Analytics & Pattern Detection Types
// ============================================================================

export interface ErrorTrend {
  date: string;
  error_count: number;
  resolved_count: number;
  avg_resolution_time_hours: number;
}

export interface PatternCluster {
  cluster_id: string;
  cluster_name: string;
  member_count: number;
  avg_quality_score: number;
  summary: string;
  representative_memory_ids: string[];
  tags: string[];
}

export interface KnowledgeGap {
  gap_id: string;
  area: string;
  description: string;
  severity: "high" | "medium" | "low";
  related_errors: string[];
  suggested_actions: string[];
}

export interface Recommendation {
  memory_id: string;
  content: string;
  reason: string;
  relevance_score: number;
  quality_score: number;
  tags: string[];
}

export interface ErrorSpike {
  date: string;
  error_count: number;
  spike_severity: number;
  common_tags: string[];
  common_errors: string[];
}

export interface RecurringError {
  error_pattern: string;
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
  memory_ids: string[];
  resolution_rate: number;
}

export interface ResolutionTime {
  avg_resolution_hours: number;
  median_resolution_hours: number;
  fastest_resolution_hours: number;
  slowest_resolution_hours: number;
  total_resolved: number;
}

export interface ExpertiseCluster {
  area: string;
  memory_count: number;
  avg_quality: number;
  key_contributors: string[];
  representative_memories: string[];
}
