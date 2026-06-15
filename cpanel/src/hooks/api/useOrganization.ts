import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface Organization {
  id: string;
  name: string;
  email?: string;
  created_at: string;
}

export interface OrganizationCreatePayload {
  name: string;
  email?: string;
}

export function useOrganizationHooks() {
  const queryClient = useQueryClient();

  const useOrganizationsQuery = () => {
    return useQuery({
      queryKey: ['organizations'],
      queryFn: async () => {
        const { data } = await apiClient.get<Organization[]>('/organizations');
        return data;
      },
    });
  };

  const useCreateOrganizationMutation = () => {
    return useMutation({
      mutationFn: async (payload: OrganizationCreatePayload) => {
        const { data } = await apiClient.post<Organization>('/organizations', payload);
        return data;
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['organizations'] });
      },
    });
  };

  return {
    useOrganizationsQuery,
    useCreateOrganizationMutation,
  };
}
