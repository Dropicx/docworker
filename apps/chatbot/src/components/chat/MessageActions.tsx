/**
 * MessageActions component for chat messages.
 *
 * Displays like/dislike feedback buttons and copy button at the bottom
 * of assistant messages. Includes optional reason input for dislikes.
 */

import React, { useState, useCallback } from 'react';
import { ThumbsUp, ThumbsDown, Copy, Check, Loader2, Send } from 'lucide-react';
import { useFeedback } from '../../hooks/useFeedback';

interface MessageActionsProps {
  messageId: string;
  conversationId?: string;
  content: string;
}

export const MessageActions: React.FC<MessageActionsProps> = ({
  messageId,
  conversationId,
  content,
}) => {
  const { feedback, isSubmitting, submitFeedback } = useFeedback(messageId, {
    conversationId,
  });

  const [copied, setCopied] = useState(false);
  const [showReasonInput, setShowReasonInput] = useState(false);
  const [reason, setReason] = useState('');

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [content]);

  const handleLike = useCallback(async () => {
    // If currently showing reason input, hide it
    if (showReasonInput) {
      setShowReasonInput(false);
      setReason('');
    }
    await submitFeedback('like');
  }, [submitFeedback, showReasonInput]);

  const handleDislike = useCallback(async () => {
    // If already disliked, toggle off
    if (feedback === 'dislike') {
      await submitFeedback('dislike'); // Will toggle off
      setShowReasonInput(false);
      setReason('');
      return;
    }

    // Show reason input for new dislike
    setShowReasonInput(true);
  }, [feedback, submitFeedback]);

  const handleSubmitDislike = useCallback(async () => {
    await submitFeedback('dislike', reason || undefined);
    setShowReasonInput(false);
    setReason('');
  }, [submitFeedback, reason]);

  const handleCancelReason = useCallback(() => {
    setShowReasonInput(false);
    setReason('');
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmitDislike();
      } else if (e.key === 'Escape') {
        handleCancelReason();
      }
    },
    [handleSubmitDislike, handleCancelReason]
  );

  return (
    <div className="mt-2">
      {/* Action buttons */}
      <div className="flex items-center gap-1">
        {/* Like button */}
        <button
          onClick={handleLike}
          disabled={isSubmitting}
          className={`p-1.5 rounded transition-colors ${
            feedback === 'like'
              ? 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/30'
              : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title={feedback === 'like' ? 'Gefällt mir nicht mehr' : 'Gefällt mir'}
          aria-label={feedback === 'like' ? 'Remove like' : 'Like'}
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ThumbsUp
              className={`w-4 h-4 ${feedback === 'like' ? 'fill-current' : ''}`}
            />
          )}
        </button>

        {/* Dislike button */}
        <button
          onClick={handleDislike}
          disabled={isSubmitting}
          className={`p-1.5 rounded transition-colors ${
            feedback === 'dislike'
              ? 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30'
              : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title={feedback === 'dislike' ? 'Gefällt mir doch' : 'Gefällt mir nicht'}
          aria-label={feedback === 'dislike' ? 'Remove dislike' : 'Dislike'}
        >
          <ThumbsDown
            className={`w-4 h-4 ${feedback === 'dislike' ? 'fill-current' : ''}`}
          />
        </button>

        {/* Separator */}
        <div className="w-px h-4 bg-neutral-200 dark:bg-neutral-700 mx-1" />

        {/* Copy button */}
        <button
          onClick={handleCopy}
          className="p-1.5 text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded transition-colors"
          title={copied ? 'Kopiert!' : 'Kopieren'}
          aria-label={copied ? 'Copied' : 'Copy'}
        >
          {copied ? (
            <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
          ) : (
            <Copy className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Reason input for dislike */}
      {showReasonInput && (
        <div className="mt-2 p-2 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg border border-neutral-200 dark:border-neutral-700">
          <label className="block text-xs text-neutral-500 dark:text-neutral-400 mb-1.5">
            Was war nicht hilfreich? (optional)
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="z.B. Unvollständige Antwort..."
              className="flex-1 px-2 py-1.5 text-sm bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-600 rounded focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 text-neutral-800 dark:text-neutral-100 placeholder-neutral-400 dark:placeholder-neutral-500"
              maxLength={500}
              autoFocus
            />
            <button
              onClick={handleSubmitDislike}
              disabled={isSubmitting}
              className="px-2 py-1.5 bg-brand-600 hover:bg-brand-700 dark:bg-brand-500 dark:hover:bg-brand-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Feedback senden"
              aria-label="Submit feedback"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
            <button
              onClick={handleCancelReason}
              className="px-2 py-1.5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 transition-colors"
              title="Abbrechen"
              aria-label="Cancel"
            >
              &times;
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageActions;
