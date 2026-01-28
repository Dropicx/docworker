/**
 * TypeScript types for GuidelineChat feature
 */

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
}

export interface ChatConversation {
  id: string;
  difyConversationId?: string;
  appId: string;  // Which Dify app this conversation uses
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

export interface ChatApp {
  id: string;
  name: string;
  description: string;
  icon: string;
  available: boolean;
}

export interface ChatStorageSchema {
  conversations: ChatConversation[];
  activeConversationId: string | null;
}

export interface ChatStreamEvent {
  event: 'message' | 'message_end' | 'error' | 'agent_message' | 'agent_thought';
  answer?: string;
  conversation_id?: string;
  message_id?: string;
  task_id?: string;
  id?: string;
  created_at?: number;
  message?: string;
  code?: string;
}

export interface ChatRequest {
  query: string;
  conversation_id?: string;
}

export interface RateLimitError {
  error: 'rate_limit_exceeded';
  message: string;
  retry_after: number | null;
  limit_type: 'minute' | 'hour' | 'day' | 'temp_ban' | 'permanent_ban' | null;
}

export interface RateLimitStatus {
  messages_minute: number;
  messages_hour: number;
  messages_day: number;
  limits: {
    minute: number;
    hour: number;
    day: number;
  };
  remaining_minute: number;
  remaining_hour: number;
  remaining_day: number;
  banned: boolean;
  temp_ban_until?: string;
}
