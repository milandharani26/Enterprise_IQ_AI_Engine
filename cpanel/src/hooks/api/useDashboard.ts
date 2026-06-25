import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface DashboardMetrics {
  total_assistants: number;
  active_connectors: number;
  total_credentials: number;
  total_conversations: number;
  total_messages: number;
  system_health: string;
  recent_conversations: {
    id: string;
    title: string;
    created_at: string;
  }[];
  activity_chart: {
    date: string;
    conversations: number;
    messages: number;
  }[];
  knowledge_composition: {
    source: string;
    count: number;
  }[];
  top_assistants: {
    name: string;
    conversations: number;
  }[];
}

export const useDashboardHooks = () => {
  const useDashboardMetricsQuery = (organizationId: string | null) => {
    return useQuery({
      queryKey: ['dashboard_metrics', organizationId],
      queryFn: async () => {
        if (!organizationId) return null;
        const { data } = await axios.get(`${API_URL}/dashboard/metrics/${organizationId}`);
        return data as DashboardMetrics;
      },
      enabled: !!organizationId,
      refetchInterval: 30000, // Refresh every 30 seconds
    });
  };

  return {
    useDashboardMetricsQuery,
  };
};
