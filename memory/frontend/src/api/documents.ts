import { apiClient } from './client';

export interface DocumentStats {
  collection: string;
  total_chunks: number;
  status: string;
  error?: string;
}

export interface DocumentSearchQuery {
  query: string;
  limit?: number;
  score_threshold?: number;
}

export interface DocumentSearchResult {
  id: string;
  file_path: string;
  chunk_index: number;
  content: string;
  score: number;
  metadata?: Record<string, any>;
}

export const getDocumentStats = () =>
  apiClient.get<DocumentStats>('/documents/stats').then(r => r.data);

export const searchDocuments = (query: DocumentSearchQuery) =>
  apiClient.post<DocumentSearchResult[]>('/documents/search', query).then(r => r.data);

export const deleteDocument = (filePath: string) =>
  apiClient.delete(`/documents/${encodeURIComponent(filePath)}`);

export const resetDocuments = (confirm: boolean = false) =>
  apiClient.post('/documents/reset', null, { params: { confirm } }).then(r => r.data);
