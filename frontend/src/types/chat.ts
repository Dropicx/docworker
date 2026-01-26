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
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
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
