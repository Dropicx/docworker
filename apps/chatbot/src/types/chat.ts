/**
 * TypeScript types for GuidelineChat feature
 */

export interface RetrieverResource {
  document_name: string;
  segment_id: string;
  score: number;
  content_preview?: string;  // From our backend (sanitized)
  content?: string;  // From raw Dify response (fallback)
}

export interface SuggestedQuestionsResponse {
  questions: string[];
  message_id: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  messageId?: string;  // Dify message ID for suggested questions
  retrieverResources?: RetrieverResource[];  // Citations/sources
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
  retriever_resources?: RetrieverResource[];  // Citations from message_end event (processed by backend)
  metadata?: {  // Raw Dify metadata (fallback)
    retriever_resources?: RetrieverResource[];
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
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

// Message feedback types
export type FeedbackType = 'like' | 'dislike' | null;

export interface MessageFeedback {
  message_id: string;
  feedback: FeedbackType;
  reason?: string | null;
  submitted_at?: string | null;
}

export interface FeedbackRequest {
  message_id: string;
  conversation_id?: string;
  feedback: 'like' | 'dislike';
  reason?: string;
}

export interface FeedbackDeleteResponse {
  message_id: string;
  deleted: boolean;
}
