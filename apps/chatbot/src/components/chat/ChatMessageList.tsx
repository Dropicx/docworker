/**
 * Scrollable message list component.
 *
 * Smart auto-scroll: only scrolls to bottom if user is already near bottom.
 * Allows free scrolling during streaming responses.
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { BookOpen, MessageCircle, ArrowDown } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import { ChatMessage } from './ChatMessage';

interface ChatMessageListProps {
  messages: ChatMessageType[];
  isStreaming?: boolean;
  conversationId?: string;
}

export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  isStreaming = false,
  conversationId,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Check if user is at or near the bottom (within 100px threshold)
  const checkIfAtBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) return true;

    const threshold = 100;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    return distanceFromBottom <= threshold;
  }, []);

  // Handle scroll events
  const handleScroll = useCallback(() => {
    const atBottom = checkIfAtBottom();
    setIsAtBottom(atBottom);
    setShowScrollButton(!atBottom && messages.length > 0);
  }, [checkIfAtBottom, messages.length]);

  // Scroll to bottom function
  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({
      behavior: smooth ? 'smooth' : 'auto'
    });
    setIsAtBottom(true);
    setShowScrollButton(false);
  }, []);

  // Auto-scroll only when user is at bottom
  useEffect(() => {
    if (isAtBottom) {
      // Use instant scroll during streaming for smoother experience
      scrollToBottom(!isStreaming);
    } else if (isStreaming) {
      // Show scroll button when streaming and user has scrolled up
      setShowScrollButton(true);
    }
  }, [messages, isStreaming, isAtBottom, scrollToBottom]);

  // Scroll to bottom when a new conversation starts (first message)
  useEffect(() => {
    if (messages.length === 1) {
      scrollToBottom(false);
    }
  }, [messages.length, scrollToBottom]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto flex items-center justify-center p-8 bg-neutral-50 dark:bg-neutral-900">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-accent-100 dark:bg-accent-900/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <BookOpen className="w-8 h-8 text-accent-600 dark:text-accent-400" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-2">
            Frag die Leitlinie
          </h3>
          <p className="text-neutral-600 dark:text-neutral-400 mb-6">
            Stellen Sie Fragen zu deutschen medizinischen Leitlinien (AWMF).
            Der Assistent durchsucht die Leitlinien-Datenbank und gibt Ihnen
            fundierte Antworten.
          </p>
          <div className="space-y-2 text-sm text-neutral-500 dark:text-neutral-400">
            <p className="flex items-center justify-center gap-2">
              <MessageCircle className="w-4 h-4" />
              Beispiel: "Was sind die Empfehlungen bei Diabetes Typ 2?"
            </p>
            <p className="flex items-center justify-center gap-2">
              <MessageCircle className="w-4 h-4" />
              Beispiel: "Wie wird Bluthochdruck behandelt?"
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex-1 overflow-hidden">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto p-4 space-y-4 bg-neutral-50 dark:bg-neutral-900 scrollbar-thin"
      >
        {messages.map(message => (
          <ChatMessage key={message.id} message={message} conversationId={conversationId} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button
          onClick={() => scrollToBottom(true)}
          className="absolute bottom-4 right-4 p-3 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-full shadow-medium hover:shadow-hard hover:bg-neutral-50 dark:hover:bg-neutral-700 transition-all z-10"
          title="Nach unten scrollen"
        >
          <ArrowDown className="w-5 h-5 text-neutral-600 dark:text-neutral-300" />
        </button>
      )}
    </div>
  );
};

export default ChatMessageList;
