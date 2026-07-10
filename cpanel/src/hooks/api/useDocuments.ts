import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface DocumentRecord {
  id: string;
  workspace_id: string;
  reference_id: string;
  title?: string;
  source?: string;
  status: 'draft' | 'processing' | 'indexed' | 'failed';
  chunk_count: number;
  processing_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResult {
  success: boolean;
  status_code: number;
  message: string;
  data: {
    doc_id: string;
    reference_id: string;
    status: string;
    message: string;
    chunk_count?: number;
    processing_error?: string | null;
  };
}

export interface DocumentListResponse {
  success: boolean;
  status_code: number;
  message: string;
  data: DocumentRecord[];
  meta: {
    pagination: {
      total: number;
      offset: number;
      limit: number;
      total_pages: number;
      has_more: boolean;
    };
  };
}

export const documentKeys = {
  all: ['documents'] as const,
  lists: () => [...documentKeys.all, 'list'] as const,
  list: (orgId: string) => [...documentKeys.lists(), orgId] as const,
  status: (docId: string) => [...documentKeys.all, 'status', docId] as const,
};

export function useDocumentsHooks() {
  const queryClient = useQueryClient();

  const useDocumentsQuery = (organizationId?: string | null, options?: { pollWhileProcessing?: boolean }) =>
    useQuery({
      queryKey: documentKeys.list(organizationId || 'none'),
      queryFn: async () => {
        const { data } = await apiClient.get<DocumentListResponse>('/documents', {
          params: { organization_id: organizationId },
        });
        return data;
      },
      enabled: !!organizationId,
      refetchInterval: (query) => {
        if (!options?.pollWhileProcessing) return false;
        const docs = query.state.data?.data || [];
        const pending = docs.some((d) => d.status === 'processing' || d.status === 'draft');
        return pending ? 3000 : false;
      },
    });

  const useUploadDocumentMutation = () =>
    useMutation({
      mutationFn: async ({
        file,
        organizationId,
        title,
      }: {
        file: File;
        organizationId: string;
        title?: string;
      }) => {
        const form = new FormData();
        form.append('file', file);
        form.append('organization_id', organizationId);
        if (title) form.append('title', title);
        const { data } = await apiClient.post<DocumentUploadResult>('/documents/upload', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        return data;
      },
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: documentKeys.list(variables.organizationId) });
      },
    });

  const useDeleteDocumentMutation = () =>
    useMutation({
      mutationFn: async ({ documentId, organizationId }: { documentId: string; organizationId: string }) => {
        await apiClient.delete(`/documents/${documentId}`);
        return organizationId;
      },
      onSuccess: (organizationId) => {
        queryClient.invalidateQueries({ queryKey: documentKeys.list(organizationId) });
      },
    });

  const pollIngestionStatus = async (documentId: string): Promise<string> => {
    const { data } = await apiClient.get<{
      data: { document_id: string; status: string };
    }>(`/documents/ingestion-status/${documentId}`);
    return data.data.status;
  };

  return {
    useDocumentsQuery,
    useUploadDocumentMutation,
    useDeleteDocumentMutation,
    pollIngestionStatus,
  };
}
