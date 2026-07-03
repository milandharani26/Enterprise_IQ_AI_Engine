import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'react-hot-toast';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface Credential {
  id: string;
  organization_id: string;
  name: string;
  provider: string;
  status: string;
  created_at: string;
  updated_at: string;
  last_used_at: string | null;
  display_info?: {
    email?: string;
    host?: string;
    username?: string;
  };
  sync_status?: string;
}

export const useCredentialsHooks = () => {
  const queryClient = useQueryClient();

  const useCredentialsQuery = (organizationId: string | null) => {
    return useQuery({
      queryKey: ['credentials', organizationId],
      queryFn: async () => {
        if (!organizationId) return [];
        const { data } = await axios.get(`${API_URL}/credentials/organization/${organizationId}`);
        return data as Credential[];
      },
      enabled: !!organizationId,
    });
  };

  const useAddCredentialMutation = () => {
    return useMutation({
      mutationFn: async (newCredential: { organization_id: string; name: string; provider: string; auth_data: any }) => {
        const { data } = await axios.post(`${API_URL}/credentials/`, newCredential);
        return data as Credential;
      },
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries({ queryKey: ['credentials', variables.organization_id] });
        toast.success('Credential created successfully');
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to create credential');
      },
    });
  };

  const useDeleteCredentialMutation = () => {
    return useMutation({
      mutationFn: async (credentialId: string) => {
        await axios.delete(`${API_URL}/credentials/${credentialId}`);
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['credentials'] });
        queryClient.invalidateQueries({ queryKey: ['connectors'] });
        toast.success('Credential deleted');
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to delete credential');
      },
    });
  };

  const useTestCredentialMutation = () => {
    return useMutation({
      mutationFn: async (testData: { provider: string; auth_data: any }) => {
        const { data } = await axios.post(`${API_URL}/credentials/test`, testData);
        return data as { success: boolean; message: string };
      },
      onSuccess: (data) => {
        if (data.success) {
          toast.success(data.message || 'Connection successful!');
        } else {
          toast.error(data.message || 'Connection failed.');
        }
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.message || 'Error connecting to provider.');
      },
    });
  };

  const useGenerateGoogleOAuthUrlMutation = () => {
    return useMutation({
      mutationFn: async (payload: { name: string; organization_id: string; client_id: string; client_secret: string; redirect_uri: string }) => {
        const { data } = await axios.post(`${API_URL}/credentials/oauth/google/generate-url`, payload);
        return data as { auth_url: string; state: string };
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to generate OAuth URL');
      },
    });
  };

  const useRegenerateGoogleOAuthUrlMutation = () => {
    return useMutation({
      mutationFn: async (credentialId: string) => {
        const { data } = await axios.post(`${API_URL}/credentials/oauth/google/${credentialId}/regenerate-url`);
        return data as { auth_url: string; state: string };
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to regenerate OAuth URL');
      },
    });
  };

  const useExchangeGoogleOAuthCodeMutation = () => {
    return useMutation({
      mutationFn: async (payload: { code: string; state: string }) => {
        const { data } = await axios.post(`${API_URL}/credentials/oauth/google/exchange`, payload);
        return data as Credential;
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['credentials'] });
        toast.success('Google Drive connected successfully!');
      },
      onError: (error: any) => {
        toast.error(error?.response?.data?.detail || 'Failed to connect Google Drive');
      },
    });
  };

  return {
    useCredentialsQuery,
    useAddCredentialMutation,
    useDeleteCredentialMutation,
    useTestCredentialMutation,
    useGenerateGoogleOAuthUrlMutation,
    useRegenerateGoogleOAuthUrlMutation,
    useExchangeGoogleOAuthCodeMutation,
  };
};
