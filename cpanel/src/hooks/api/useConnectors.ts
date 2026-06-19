import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'react-hot-toast';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Connector {
  id: string;
  organization_id: string;
  connector_id: string;
  name: string;
  provider: string;
  status: string; // 'enabled' | 'disabled'
  credential_id: string | null;
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
        const { data } = await axios.get(`${API_URL}/connectors/organization/${organizationId}`);
        return data as Connector[];
      },
      enabled: !!organizationId,
    });
  };

  const useAddConnectorMutation = () => {
    return useMutation({
      mutationFn: async (newConnector: { organization_id: string; connector_id: string; name: string; provider: string; status?: string; credential_id?: string | null }) => {
        const { data } = await axios.post(`${API_URL}/connectors/`, newConnector);
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
        const { data } = await axios.patch(`${API_URL}/connectors/${id}`, updates);
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

  return {
    useConnectorsQuery,
    useAddConnectorMutation,
    useUpdateConnectorMutation,
  };
};
