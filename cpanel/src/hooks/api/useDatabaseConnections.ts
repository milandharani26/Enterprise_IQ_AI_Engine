import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

export interface DatabaseConnection {
  id: string;
  organization_id: string;
  name: string;
  database_type: string;
  host: string;
  port: number;
  database_name: string;
  schema_name?: string;
  username: string;
  is_active: boolean;
  sync_status?: string;
  last_synced_at?: string;
  created_at: string;
}

export const useDatabaseConnections = () => {
  return useQuery({
    queryKey: ["database-connections"],
    queryFn: async () => {
      const response = await apiClient.get<{ data: DatabaseConnection[] }>("/database-connections");
      return response.data.data;
    },
  });
};

export const useCreateDatabaseConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<DatabaseConnection> & { password?: string }) => {
      const response = await apiClient.post("/database-connections", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
};

export const useTestDatabaseConnection = () => {
  return useMutation({
    mutationFn: async (data: Partial<DatabaseConnection> & { password?: string }) => {
      const response = await apiClient.post("/database-connections/test", data);
      return response.data;
    },
  });
};

export const useSyncDatabaseConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.post(`/database-connections/${id}/sync`);
      return response.data;
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
      queryClient.invalidateQueries({ queryKey: ["database-connection", id] });
    },
  });
};

export const useDeleteDatabaseConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.delete(`/database-connections/${id}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
};

export const useUpdateDatabaseConnection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<DatabaseConnection> & { password?: string } }) => {
      const response = await apiClient.put(`/database-connections/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
};

