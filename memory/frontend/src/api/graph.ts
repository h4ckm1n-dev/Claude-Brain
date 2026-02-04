import { apiClient } from './client';

export interface ProjectGraph {
  nodes: Array<{ id: string; type: string; label: string; project: string }>;
  edges: Array<{ source: string; target: string; relation: string }>;
}

export interface Contradiction {
  memory_a: { id: string; content: string; type: string };
  memory_b: { id: string; content: string; type: string };
  relation: string;
  detected_at: string;
}

export interface GraphSolution {
  error_id: string;
  solutions: Array<{ id: string; content: string; score: number; relation: string }>;
}

export interface GraphRecommendation {
  id: string;
  content: string;
  type: string;
  score: number;
  relation_path: string[];
}

export const getProjectGraph = (project: string) =>
  apiClient.get<ProjectGraph>(`/graph/project/${encodeURIComponent(project)}`).then(r => r.data);

export const findSolutions = (errorId: string) =>
  apiClient.get<GraphSolution>(`/graph/solutions/${errorId}`).then(r => r.data);

export const getContradictions = () =>
  apiClient.get<Contradiction[]>('/graph/contradictions').then(r => r.data);

export const getGraphRecommendations = (memoryId: string, limit: number = 10) =>
  apiClient.get<GraphRecommendation[]>(`/graph/recommendations/${memoryId}`, {
    params: { limit }
  }).then(r => r.data);
