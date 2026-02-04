/**
 * Scrollable message list component.
 */

import React, { useRef, useEffect } from 'react';
import { BookOpen, MessageCircle } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import { ChatMessage } from './ChatMessage';

interface ChatMessageListProps {
  messages: ChatMessageType[];
  isStreaming?: boolean;
}

export const ChatMessageList: React.FC<ChatMessageListProps> = ({
  messages,
  isStreaming = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-accent-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <BookOpen className="w-8 h-8 text-accent-600" />
          </div>
          <h3 className="text-xl font-semibold text-neutral-800 mb-2">
            GuidelineChat
          </h3>
          <p className="text-neutral-600 mb-6">
            Stellen Sie Fragen zu deutschen medizinischen Leitlinien (AWMF).
            Der Assistent durchsucht die Leitlinien-Datenbank und gibt Ihnen
            fundierte Antworten.
          </p>
          <div className="space-y-2 text-sm text-neutral-500">
            <p className="flex items-center justify-center gap-2">
              <MessageCircle className="w-4 h-4" />
              Beispiel: &ldquo;Was sind die Empfehlungen bei Diabetes Typ 2?&rdquo;
            </p>
            <p className="flex items-center justify-center gap-2">
              <MessageCircle className="w-4 h-4" />
              Beispiel: &ldquo;Wie wird Bluthochdruck behandelt?&rdquo;
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 space-y-4 bg-neutral-50"
    >
      {messages.map(message => (
        <ChatMessage key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default ChatMessageList;
