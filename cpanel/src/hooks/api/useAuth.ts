import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAppStore } from '@/store/useAppStore';

export const useAuthHooks = () => {
  const queryClient = useQueryClient();
  const setUser = useAppStore((state) => state.setUser);
  const logoutState = useAppStore((state) => state.logout);

  const useLoginMutation = () => useMutation({
    mutationFn: async (credentials: Record<string, any>) => {
      const response = await apiClient.post('/auth/login', credentials);
      return response.data;
    },
    onSuccess: (data) => {
      // Assuming response has user info, or we might need to fetch it separately.
      // If the backend returns user object, we can set it. Otherwise, set a basic mock user
      // or make a follow-up request to get `/users/me`.
      // For now, we'll set a generic user so `isAuthenticated` becomes true.
      setUser({ email: data.email || 'user@example.com' });
    },
  });

  const useLogoutMutation = () => useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/auth/logout');
      return response.data;
    },
    onSuccess: () => {
      logoutState();
      queryClient.clear();
    },
  });

  return {
    useLoginMutation,
    useLogoutMutation,
  };
};
