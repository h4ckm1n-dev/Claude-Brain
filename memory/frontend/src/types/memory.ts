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

export interface ConsolidateResult {
  analyzed: number;
  consolidated: number;
  archived: number;
  deleted: number;
  kept: number;
  dry_run: boolean;
  details?: any;
}
