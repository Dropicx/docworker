/**
 * Chat API Service for GuidelineChat
 *
 * Uses fetch API for SSE streaming (axios doesn't support SSE well).
 * Includes session token management and rate limit handling.
 */

import { ChatStreamEvent, ChatApp, RateLimitError, RateLimitStatus } from '../types/chat';

// Base API URL
const API_URL = import.meta.env.VITE_API_URL || '/api';

// Session token storage key
const SESSION_TOKEN_KEY = 'chat_session_token';

/**
 * Get or create a chat session token for rate limiting.
 * Uses crypto.randomUUID() for secure token generation.
 */
function getChatSessionToken(): string {
  let token = localStorage.getItem(SESSION_TOKEN_KEY);
  if (!token) {
    token = crypto.randomUUID();
    localStorage.setItem(SESSION_TOKEN_KEY, token);
  }
  return token;
}

/**
 * Get common headers for chat API requests.
 */
function getChatHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    'X-Chat-Session': getChatSessionToken(),
  };
}

/**
 * Custom error class for rate limit errors.
 */
export class ChatRateLimitError extends Error {
  public readonly retryAfter: number | null;
  public readonly limitType: string | null;

  constructor(data: RateLimitError) {
    super(data.message);
    this.name = 'ChatRateLimitError';
    this.retryAfter = data.retry_after;
    this.limitType = data.limit_type;
  }
}

/**
 * Fetch available chat apps from the backend.
 */
export async function getChatApps(): Promise<ChatApp[]> {
  try {
    const response = await fetch(`${API_URL}/chat/apps`, {
      headers: getChatHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch apps: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Failed to fetch chat apps:', error);
    // Return default apps if fetch fails
    return [
      {
        id: 'guidelines',
        name: 'Leitlinien Q&A',
        description: 'Fragen zu AWMF-Leitlinien beantworten',
        icon: 'book-open',
        available: true,
      },
    ];
  }
}

/**
 * Stream chat message from the backend (SSE).
 *
 * @param query - The user's message
 * @param conversationId - Optional Dify conversation ID for context
 * @param appId - Which Dify app to use (default: guidelines)
 * @param signal - Optional AbortSignal for cancellation
 * @yields ChatStreamEvent objects as they arrive
 * @throws ChatRateLimitError if rate limited
 */
export async function* streamChatMessage(
  query: string,
  conversationId?: string,
  appId: string = 'guidelines',
  signal?: AbortSignal
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${API_URL}/chat/message`, {
    method: 'POST',
    headers: getChatHeaders(),
    body: JSON.stringify({
      query,
      conversation_id: conversationId,
      app_id: appId,
    }),
    signal,
  });

  // Handle rate limit error
  if (response.status === 429) {
    const errorData: RateLimitError = await response.json();
    throw new ChatRateLimitError(errorData);
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chat API error: ${response.status} - ${errorText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        // Process any remaining buffer
        if (buffer.trim()) {
          const events = parseSSEBuffer(buffer);
          for (const event of events) {
            yield event;
          }
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE events from buffer
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      const events = parseSSELines(lines);
      for (const event of events) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Parse SSE lines into events.
 */
function parseSSELines(lines: string[]): ChatStreamEvent[] {
  const events: ChatStreamEvent[] = [];
  let currentData = '';

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);

      // Handle [DONE] marker
      if (data === '[DONE]') {
        continue;
      }

      // Accumulate data (multi-line data)
      currentData += data;
    } else if (line === '' && currentData) {
      // Empty line marks end of event
      try {
        const parsed = JSON.parse(currentData);
        events.push(parsed);
      } catch {
        // Ignore parse errors for incomplete data
        console.warn('Failed to parse SSE data:', currentData);
      }
      currentData = '';
    }
  }

  // Don't forget data without trailing empty line
  if (currentData) {
    try {
      const parsed = JSON.parse(currentData);
      events.push(parsed);
    } catch {
      // Will be handled in next iteration
    }
  }

  return events;
}

/**
 * Parse remaining buffer at end of stream.
 */
function parseSSEBuffer(buffer: string): ChatStreamEvent[] {
  const lines = buffer.split('\n');
  return parseSSELines(lines);
}

/**
 * Check chat service health.
 */
export async function checkChatHealth(): Promise<{
  status: string;
  url?: string;
  error?: string;
}> {
  try {
    const response = await fetch(`${API_URL}/chat/health`, {
      headers: getChatHeaders(),
    });
    return await response.json();
  } catch (error) {
    return {
      status: 'error',
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get current rate limit status for this client.
 */
export async function getRateLimitStatus(): Promise<RateLimitStatus> {
  const response = await fetch(`${API_URL}/chat/rate-limit-status`, {
    headers: getChatHeaders(),
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch rate limit status: ${response.status}`);
  }
  return await response.json();
}

/**
 * Format retry time for display.
 */
export function formatRetryTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds} Sekunden`;
  } else if (seconds < 3600) {
    const minutes = Math.ceil(seconds / 60);
    return `${minutes} Minute${minutes !== 1 ? 'n' : ''}`;
  } else {
    const hours = Math.ceil(seconds / 3600);
    return `${hours} Stunde${hours !== 1 ? 'n' : ''}`;
  }
}
