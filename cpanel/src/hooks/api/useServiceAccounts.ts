import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface ServiceAccount {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  expires_at?: string;
  created_at?: string;
}

export const serviceAccountKeys = {
  all: ['service-accounts'] as const,
  lists: () => [...serviceAccountKeys.all, 'list'] as const,
};

export const useServiceAccountsHooks = () => {
  const queryClient = useQueryClient();

  const useServiceAccountsQuery = () => useQuery({
    queryKey: serviceAccountKeys.lists(),
    queryFn: async () => {
      const response = await apiClient.get<ServiceAccount[]>('/service-accounts');
      return response.data;
    },
  });

  const useCreateServiceAccountMutation = () => useMutation({
    mutationFn: async (data: Partial<ServiceAccount>) => {
      const response = await apiClient.post<{ account: ServiceAccount; token: string }>('/service-accounts', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: serviceAccountKeys.lists() });
    },
  });

  const useRevokeServiceAccountMutation = () => useMutation({
    mutationFn: async (accountId: string) => {
      const response = await apiClient.post(`/service-accounts/${accountId}/revoke`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: serviceAccountKeys.lists() });
    },
  });

  const useRegenerateServiceAccountMutation = () => useMutation({
    mutationFn: async ({ accountId, data }: { accountId: string; data?: { expires_at: string } }) => {
      const response = await apiClient.post<{ account: ServiceAccount; token: string }>(`/service-accounts/${accountId}/regenerate`, data || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: serviceAccountKeys.lists() });
    },
  });

  return {
    useServiceAccountsQuery,
    useCreateServiceAccountMutation,
    useRevokeServiceAccountMutation,
    useRegenerateServiceAccountMutation,
  };
};
