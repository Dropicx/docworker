/**
 * Custom hook for managing message feedback state.
 *
 * Handles like/dislike feedback for assistant messages,
 * syncing with the backend API and caching in memory.
 */

import { useState, useCallback, useEffect } from 'react';
import { FeedbackType, MessageFeedback } from '../types/chat';
import {
  submitMessageFeedback,
  getMessageFeedback,
  deleteMessageFeedback,
} from '../services/chatApi';

interface UseFeedbackOptions {
  conversationId?: string;
  onError?: (error: Error) => void;
}

interface UseFeedbackReturn {
  feedback: FeedbackType;
  reason: string | null;
  isSubmitting: boolean;
  submitFeedback: (type: 'like' | 'dislike', reason?: string) => Promise<void>;
  removeFeedback: () => Promise<void>;
}

/**
 * Hook for managing feedback on a single message.
 *
 * @param messageId - The ID of the message to manage feedback for
 * @param options - Optional configuration (conversationId, error handler)
 */
export function useFeedback(
  messageId: string,
  options: UseFeedbackOptions = {}
): UseFeedbackReturn {
  const { conversationId, onError } = options;

  const [feedback, setFeedback] = useState<FeedbackType>(null);
  const [reason, setReason] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch existing feedback on mount
  useEffect(() => {
    let mounted = true;

    const fetchFeedback = async () => {
      try {
        const result = await getMessageFeedback(messageId);
        if (mounted && result.feedback) {
          setFeedback(result.feedback as FeedbackType);
          setReason(result.reason ?? null);
        }
      } catch (error) {
        // Silently fail - feedback may not exist yet
        console.debug('No existing feedback for message:', messageId);
      }
    };

    fetchFeedback();

    return () => {
      mounted = false;
    };
  }, [messageId]);

  /**
   * Submit feedback (like or dislike).
   * If the same feedback type is submitted again, it toggles off (removes).
   */
  const submitFeedback = useCallback(
    async (type: 'like' | 'dislike', feedbackReason?: string) => {
      // If clicking the same type, remove feedback (toggle off)
      if (feedback === type) {
        await removeFeedback();
        return;
      }

      setIsSubmitting(true);

      try {
        const result = await submitMessageFeedback({
          message_id: messageId,
          conversation_id: conversationId,
          feedback: type,
          reason: feedbackReason,
        });

        setFeedback(result.feedback as FeedbackType);
        setReason(result.reason ?? null);
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Failed to submit feedback');
        onError?.(err);
        console.error('Failed to submit feedback:', error);
      } finally {
        setIsSubmitting(false);
      }
    },
    [messageId, conversationId, feedback, onError]
  );

  /**
   * Remove feedback for this message.
   */
  const removeFeedback = useCallback(async () => {
    setIsSubmitting(true);

    try {
      await deleteMessageFeedback(messageId);
      setFeedback(null);
      setReason(null);
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Failed to remove feedback');
      onError?.(err);
      console.error('Failed to remove feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  }, [messageId, onError]);

  return {
    feedback,
    reason,
    isSubmitting,
    submitFeedback,
    removeFeedback,
  };
}

/**
 * Hook for managing feedback across multiple messages.
 * Useful for batch operations or caching.
 */
export function useFeedbackCache() {
  const [cache, setCache] = useState<Map<string, MessageFeedback>>(new Map());

  const updateCache = useCallback((messageId: string, feedback: MessageFeedback) => {
    setCache(prev => new Map(prev).set(messageId, feedback));
  }, []);

  const removeFromCache = useCallback((messageId: string) => {
    setCache(prev => {
      const next = new Map(prev);
      next.delete(messageId);
      return next;
    });
  }, []);

  const getCached = useCallback(
    (messageId: string): MessageFeedback | undefined => {
      return cache.get(messageId);
    },
    [cache]
  );

  return {
    cache,
    updateCache,
    removeFromCache,
    getCached,
  };
}
