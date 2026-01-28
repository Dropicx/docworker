/**
 * Custom hook for managing chat history in localStorage.
 *
 * Features:
 * - Persists conversations to localStorage
 * - Auto-generates conversation titles from first message
 * - Limits stored conversations to prevent storage issues
 * - Links Dify conversation IDs for context continuity
 */

import { useState, useEffect, useCallback } from 'react';
import { ChatMessage, ChatConversation, ChatStorageSchema } from '../types/chat';

// Storage key for fragdieleitlinie.de (separate from main app)
const STORAGE_KEY = 'fragdieleitlinie_chat_history';
const MAX_CONVERSATIONS = 50;

/**
 * Generate a UUID v4.
 */
function generateId(): string {
  return crypto.randomUUID();
}

/**
 * Generate a conversation title from the first message.
 */
function generateTitle(message: string): string {
  // Take first 50 chars, cut at word boundary
  const maxLength = 50;
  if (message.length <= maxLength) {
    return message;
  }

  const truncated = message.substring(0, maxLength);
  const lastSpace = truncated.lastIndexOf(' ');
  if (lastSpace > 20) {
    return truncated.substring(0, lastSpace) + '...';
  }
  return truncated + '...';
}

/**
 * Load chat history from localStorage.
 */
function loadFromStorage(): ChatStorageSchema {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Validate structure
      if (parsed.conversations && Array.isArray(parsed.conversations)) {
        return parsed;
      }
    }
  } catch (error) {
    console.error('Failed to load chat history:', error);
  }

  return {
    conversations: [],
    activeConversationId: null,
  };
}

/**
 * Save chat history to localStorage.
 */
function saveToStorage(state: ChatStorageSchema): void {
  try {
    // Limit conversations to prevent storage overflow
    const limitedState = {
      ...state,
      conversations: state.conversations.slice(0, MAX_CONVERSATIONS),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(limitedState));
  } catch (error) {
    console.error('Failed to save chat history:', error);
  }
}

/**
 * Hook for managing chat conversation history.
 */
export function useChatHistory() {
  const [state, setState] = useState<ChatStorageSchema>(loadFromStorage);

  // Persist to localStorage whenever state changes
  useEffect(() => {
    saveToStorage(state);
  }, [state]);

  /**
   * Create a new conversation.
   */
  const createConversation = useCallback((appId: string = 'guidelines'): ChatConversation => {
    const newConversation: ChatConversation = {
      id: generateId(),
      appId,
      title: 'Neue Unterhaltung',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setState(prev => ({
      conversations: [newConversation, ...prev.conversations],
      activeConversationId: newConversation.id,
    }));

    return newConversation;
  }, []);

  /**
   * Get or create the active conversation.
   */
  const getOrCreateActiveConversation = useCallback((): ChatConversation => {
    const existing = state.conversations.find(c => c.id === state.activeConversationId);
    if (existing) {
      return existing;
    }

    // Create new conversation if none active
    return createConversation();
  }, [state, createConversation]);

  /**
   * Add a message to the active conversation.
   */
  const addMessage = useCallback(
    (
      message: Omit<ChatMessage, 'id' | 'timestamp'>,
      conversationId?: string
    ): ChatMessage => {
      const newMessage: ChatMessage = {
        ...message,
        id: generateId(),
        timestamp: new Date().toISOString(),
      };

      setState(prev => {
        const targetId = conversationId || prev.activeConversationId;
        let conversations = prev.conversations;
        let activeId = prev.activeConversationId;

        // Find or create conversation
        let targetConv = conversations.find(c => c.id === targetId);
        if (!targetConv) {
          const newConv: ChatConversation = {
            id: generateId(),
            appId: 'guidelines', // Default app for auto-created conversations
            title: 'Neue Unterhaltung',
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
          targetConv = newConv;
          conversations = [newConv, ...conversations];
          activeId = newConv.id;
        }

        // Update conversation with new message
        conversations = conversations.map(conv => {
          if (conv.id === (targetId || activeId)) {
            const updatedConv = {
              ...conv,
              messages: [...conv.messages, newMessage],
              updatedAt: new Date().toISOString(),
            };

            // Update title from first user message
            if (
              message.role === 'user' &&
              conv.messages.filter(m => m.role === 'user').length === 0
            ) {
              updatedConv.title = generateTitle(message.content);
            }

            return updatedConv;
          }
          return conv;
        });

        return {
          conversations,
          activeConversationId: activeId,
        };
      });

      return newMessage;
    },
    []
  );

  /**
   * Update a message (for streaming updates).
   */
  const updateMessage = useCallback(
    (messageId: string, updates: Partial<ChatMessage>): void => {
      setState(prev => ({
        ...prev,
        conversations: prev.conversations.map(conv => ({
          ...conv,
          messages: conv.messages.map(msg =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          ),
          updatedAt:
            conv.messages.some(m => m.id === messageId)
              ? new Date().toISOString()
              : conv.updatedAt,
        })),
      }));
    },
    []
  );

  /**
   * Update Dify conversation ID for active conversation.
   */
  const setDifyConversationId = useCallback(
    (difyId: string, conversationId?: string): void => {
      setState(prev => ({
        ...prev,
        conversations: prev.conversations.map(conv =>
          conv.id === (conversationId || prev.activeConversationId)
            ? { ...conv, difyConversationId: difyId }
            : conv
        ),
      }));
    },
    []
  );

  /**
   * Delete a conversation.
   */
  const deleteConversation = useCallback((conversationId: string): void => {
    setState(prev => {
      const remaining = prev.conversations.filter(c => c.id !== conversationId);
      let newActiveId = prev.activeConversationId;

      // If deleted the active one, select another
      if (prev.activeConversationId === conversationId) {
        newActiveId = remaining.length > 0 ? remaining[0].id : null;
      }

      return {
        conversations: remaining,
        activeConversationId: newActiveId,
      };
    });
  }, []);

  /**
   * Set the active conversation.
   */
  const setActiveConversation = useCallback((conversationId: string | null): void => {
    setState(prev => ({
      ...prev,
      activeConversationId: conversationId,
    }));
  }, []);

  /**
   * Update conversation title.
   */
  const updateTitle = useCallback((conversationId: string, title: string): void => {
    setState(prev => ({
      ...prev,
      conversations: prev.conversations.map(conv =>
        conv.id === conversationId
          ? { ...conv, title, updatedAt: new Date().toISOString() }
          : conv
      ),
    }));
  }, []);

  /**
   * Clear all conversations.
   */
  const clearAll = useCallback((): void => {
    setState({
      conversations: [],
      activeConversationId: null,
    });
  }, []);

  // Get current active conversation
  const activeConversation = state.conversations.find(
    c => c.id === state.activeConversationId
  );

  return {
    conversations: state.conversations,
    activeConversationId: state.activeConversationId,
    activeConversation,
    createConversation,
    getOrCreateActiveConversation,
    addMessage,
    updateMessage,
    setDifyConversationId,
    deleteConversation,
    setActiveConversation,
    updateTitle,
    clearAll,
  };
}
