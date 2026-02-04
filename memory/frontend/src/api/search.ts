import { apiClient } from './client';

export interface UnifiedSearchResult {
  memories: Array<{ id: string; content: string; type: string; score: number }>;
  documents: Array<{ file_path: string; content: string; score: number; chunk_index: number }>;
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
