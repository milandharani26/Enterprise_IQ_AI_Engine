import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import toast from "react-hot-toast";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface SchemaColumnDetail {
  id: string;
  column_name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  default_value: string | null;
  column_description: string | null;
  /** True = user manually entered; sync will NOT overwrite */
  user_column_description: boolean;
  ordinal_position: number;
  updated_at: string | null;
}

export interface SchemaTableDetail {
  id: string;
  table_name: string;
  schema_name: string | null;
  table_description: string | null;
  /** True = user manually entered; sync will NOT overwrite */
  user_table_description: boolean;
  row_count_estimate: number | null;
  updated_at: string | null;
  columns: SchemaColumnDetail[];
}

// ─── Hooks ──────────────────────────────────────────────────────────────────

export const useSchemaMetadataHooks = () => {
  const queryClient = useQueryClient();

  /**
   * Fetch full schema metadata (with IDs + user-flag) for the metadata dashboard.
   */
  const useSchemaTablesDetailedQuery = (connectorId: string | null) => {
    return useQuery({
      queryKey: ["schema-metadata", connectorId],
      queryFn: async (): Promise<SchemaTableDetail[]> => {
        if (!connectorId) return [];
        const { data } = await apiClient.get(
          `/connectors/${connectorId}/tables/detailed`
        );
        return data.data as SchemaTableDetail[];
      },
      enabled: !!connectorId,
      staleTime: 30_000, // 30 s — metadata changes infrequently
    });
  };

  /**
   * PATCH a table description. Passing `null` clears the user override.
   */
  const useUpdateTableDescriptionMutation = (connectorId: string) => {
    return useMutation({
      mutationFn: async ({
        tableId,
        description,
      }: {
        tableId: string;
        description: string | null;
      }) => {
        const { data } = await apiClient.patch(
          `/connectors/${connectorId}/tables/${tableId}/description`,
          { description }
        );
        return data.data;
      },
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["schema-metadata", connectorId],
        });
        toast.success("Table description saved");
      },
      onError: (error: any) => {
        toast.error(
          error?.response?.data?.detail || "Failed to save table description"
        );
      },
    });
  };

  /**
   * PATCH a column description. Passing `null` clears the user override.
   */
  const useUpdateColumnDescriptionMutation = (connectorId: string) => {
    return useMutation({
      mutationFn: async ({
        tableId,
        columnId,
        description,
      }: {
        tableId: string;
        columnId: string;
        description: string | null;
      }) => {
        const { data } = await apiClient.patch(
          `/connectors/${connectorId}/tables/${tableId}/columns/${columnId}/description`,
          { description }
        );
        return data.data;
      },
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["schema-metadata", connectorId],
        });
        toast.success("Column description saved");
      },
      onError: (error: any) => {
        toast.error(
          error?.response?.data?.detail || "Failed to save column description"
        );
      },
    });
  };

  return {
    useSchemaTablesDetailedQuery,
    useUpdateTableDescriptionMutation,
    useUpdateColumnDescriptionMutation,
  };
};
