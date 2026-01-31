import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getDocumentStats, searchDocuments, deleteDocument, resetDocuments, DocumentSearchQuery } from '../api/documents';

export function useDocumentStats() {
  return useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: getDocumentStats,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

export function useDocumentSearch(query: DocumentSearchQuery) {
  return useQuery({
    queryKey: ['documents', 'search', query],
    queryFn: () => searchDocuments(query),
    enabled: !!query.query && query.query.length > 2,
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useResetDocuments() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resetDocuments,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
