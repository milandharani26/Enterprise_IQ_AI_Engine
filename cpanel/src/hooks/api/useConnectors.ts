import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'react-hot-toast';

export interface Connector {
  id: string;
  organization_id: string;
  connector_id: string;
  name: string;
  provider: string;
  status: string; // 'enabled' | 'disabled'
  credential_id: string | null;
  sync_status?: string | null;
  sync_error?: string | null;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export const useConnectorsHooks = () => {
  const queryClient = useQueryClient();

  const useConnectorsQuery = (organizationId: string | null) => {
    return useQuery({
      queryKey: ['connectors', organizationId],
      queryFn: async () => {
        if (!organizationId) return [];
        const { data } = await apiClient.get(`/connectors/organization/${organizationId}`);
        return data as Connector[];
      },
      enabled: !!organizationId,
      refetchInterval: (query) => {
        const data = query.state.data as Connector[] | undefined;
        // Poll every 3 seconds if any connector is actively syncing
        return data?.some(c => c.sync_status === 'syncing') ? 3000 : false;
      },
    });
  };

  const useAddConnectorMutation = () => {
    return useMutation({
      mutationFn: async (newConnector: { organization_id: string; connector_id: string; name: string; provider: string; status?: string; credential_id?: string | null }) => {
        const { data } = await apiClient.post(`/connectors/`, newConnector);
        return data as Connector;
      },
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: ['connectors', variables.organization_id] });
      },
    });
  };

  const useUpdateConnectorMutation = () => {
    return useMutation({
      mutationFn: async ({ id, updates }: { id: string; updates: { name?: string; status?: string; credential_id?: string | null } }) => {
        const { data } = await apiClient.patch(`/connectors/${id}`, updates);
        return data as Connector;
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['connectors'] });
        toast.success('Connector updated');
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to update connector');
      },
    });
  };

  const useSyncConnectorMutation = () => {
    return useMutation({
      mutationFn: async (id: string) => {
        const { data } = await apiClient.post(`/connectors/${id}/sync`);
        return data;
      },
      onSuccess: async (data) => {
        await queryClient.invalidateQueries({ queryKey: ['connectors'] });
        toast.success(data?.message || 'Connector sync started');
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to start connector sync');
      },
    });
  };

  return {
    useConnectorsQuery,
    useAddConnectorMutation,
    useUpdateConnectorMutation,
    useSyncConnectorMutation,
  };
};
