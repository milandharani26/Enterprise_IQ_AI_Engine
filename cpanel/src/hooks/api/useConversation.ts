import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface Message {
  id: string;
  conversation_id: string;
  organization_id: string;
  content: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  created_at: string;
  metadata_json?: { content_blocks?: any[] };
}

export interface NewMessagePayload {
  conversation_id: string;
  user_id: string;
  organization_id?: string;
  agent_id?: string;
  content: string;
}

export function useConversationHooks() {
  const useSendChatMessageMutation = () => {
    return useMutation({
      mutationFn: async (payload: NewMessagePayload) => {
        const { data } = await apiClient.post<Message>('/conversations/chat', payload);
        return data;
      },
    });
  };

  return {
    useSendChatMessageMutation,
  };
}
