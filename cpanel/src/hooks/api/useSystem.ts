import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export const systemKeys = {
  health: ['system-health'] as const,
  ping: ['system-ping'] as const,
};

export const useSystemHooks = () => {
  const useHealthQuery = () => useQuery({
    queryKey: systemKeys.health,
    queryFn: async () => {
      const response = await apiClient.get('/health');
      return response.data;
    },
  });

  const usePingGoogleQuery = () => useQuery({
    queryKey: systemKeys.ping,
    queryFn: async () => {
      const response = await apiClient.get('/ping-google');
      return response.data;
    },
  });

  return {
    useHealthQuery,
    usePingGoogleQuery,
  };
};
