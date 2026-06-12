import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

// Types can be extracted to a separate types file later
export interface Assistant {
  assistant_id: string;
  assistant_name: string;
  assistant_code: string;
  type: string;
  description?: string;
  category?: string;
  system_prompt?: string;
  status: string;
  guardrails?: any[];
  tools?: any[];
  prompt_library?: boolean;
  created_at?: string;
  updated_at?: string;
}

export const assistantKeys = {
  all: ['assistants'] as const,
  lists: () => [...assistantKeys.all, 'list'] as const,
  list: (filters: string) => [...assistantKeys.lists(), { filters }] as const,
  details: () => [...assistantKeys.all, 'detail'] as const,
  detail: (id: string) => [...assistantKeys.details(), id] as const,
};

export const useAssistantsHooks = () => {
  const queryClient = useQueryClient();

  const useAssistantsQuery = (skip = 0, limit = 100) => useQuery({
    queryKey: assistantKeys.list(`skip=${skip}&limit=${limit}`),
    queryFn: async () => {
      const response = await apiClient.get<Assistant[]>('/assistants', { params: { skip, limit } });
      return response.data;
    },
  });

  const useAssistantQuery = (id: string) => useQuery({
    queryKey: assistantKeys.detail(id),
    queryFn: async () => {
      const response = await apiClient.get<Assistant>(`/assistants/${id}`);
      return response.data;
    },
    enabled: !!id,
  });

  const useCreateAssistantMutation = () => useMutation({
    mutationFn: async (data: Partial<Assistant>) => {
      const response = await apiClient.post<Assistant>('/assistants', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.lists() });
    },
  });

  const useUpdateAssistantMutation = () => useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Assistant> }) => {
      const response = await apiClient.put<Assistant>(`/assistants/${id}`, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.lists() });
      queryClient.invalidateQueries({ queryKey: assistantKeys.detail(variables.id) });
    },
  });

  const useDeleteAssistantMutation = () => useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/assistants/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.lists() });
    },
  });

  const useUpdateAssistantStatusMutation = () => useMutation({
    mutationFn: async ({ id, status_in }: { id: string; status_in: { is_active: boolean } }) => {
      const response = await apiClient.patch<Assistant>(`/assistants/${id}/status`, status_in);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: assistantKeys.lists() });
      queryClient.invalidateQueries({ queryKey: assistantKeys.detail(variables.id) });
    },
  });

  return {
    useAssistantsQuery,
    useAssistantQuery,
    useCreateAssistantMutation,
    useUpdateAssistantMutation,
    useDeleteAssistantMutation,
    useUpdateAssistantStatusMutation,
  };
};
