import { apiClient } from './client';

import type { SearchResult } from '../types/memory';

export interface UnifiedSearchResult {
  query: string;
  memories: SearchResult[];
  documents: Array<{ file_path: string; content: string; score: number; chunk_index: number }>;
  total_count: number;
}

export interface EnhancedQuery {
  original: string;
  enhanced: string;
  synonyms: string[];
  corrections: string[];
}

export interface ProjectContext {
  memories: Array<{ id: string; content: string; type: string }>;
  documents?: Array<{ file_path: string; content: string }>;
  project: string;
}

export const unifiedSearch = (params: {
  query: string;
  search_memories?: boolean;
  search_documents?: boolean;
  memory_limit?: number;
  document_limit?: number;
  type_filter?: string;
  project?: string;
  use_graph_expansion?: boolean;
  use_reranking?: boolean;
  time_range_start?: string;
  time_range_end?: string;
}) =>
  apiClient.get<UnifiedSearchResult>('/search/unified', { params }).then(r => r.data);

export const enhanceQuery = (params: {
  query: string;
  expand_synonyms?: boolean;
  correct_typos?: boolean;
}) =>
  apiClient.post<EnhancedQuery>('/query/enhance', null, { params }).then(r => r.data);

export const getProjectContext = (project: string, params?: {
  hours?: number;
  types?: string;
  include_documents?: boolean;
  document_limit?: number;
}) =>
  apiClient.get<ProjectContext>(`/context/${encodeURIComponent(project)}`, { params }).then(r => r.data);
