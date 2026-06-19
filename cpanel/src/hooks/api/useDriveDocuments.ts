import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface DriveDocumentRecord {
  id: string;
  workspace_id: string;
  drive_file_id: string;
  title: string;
  mime_type: string;
  status: 'draft' | 'processing' | 'indexed' | 'failed';
  processing_error?: string;
  created_at: string;
  updated_at: string;
  chunk_count?: number;
  web_view_link?: string;
}

interface ListResponse {
  data: DriveDocumentRecord[];
  total: number;
}

export function useDriveDocumentsHooks() {
  const queryClient = useQueryClient();

  const useDriveDocumentsQuery = (
    organizationId: string | null,
    options?: { pollWhileProcessing?: boolean }
  ) => {
    return useQuery({
      queryKey: ['drive-documents', organizationId],
      queryFn: async (): Promise<ListResponse> => {
        const { data } = await apiClient.get(`/drive-documents?organization_id=${organizationId}`);
        return data;
      },
      enabled: !!organizationId,
      refetchInterval: (query) => {
        if (!options?.pollWhileProcessing) return false;
        const state = query.state.data as ListResponse | undefined;
        const hasProcessing = state?.data.some((d) => d.status === 'processing' || d.status === 'draft');
        return hasProcessing ? 3000 : false;
      },
    });
  };

  const useDeleteDriveDocumentMutation = () => {
    return useMutation({
      mutationFn: async ({ documentId }: { documentId: string; organizationId: string }) => {
        const { data } = await apiClient.delete(`/drive-documents/${documentId}`);
        return data;
      },
      onSuccess: (_, { organizationId }) => {
        queryClient.invalidateQueries({ queryKey: ['drive-documents', organizationId] });
      },
    });
  };

  return {
    useDriveDocumentsQuery,
    useDeleteDriveDocumentMutation,
  };
}
