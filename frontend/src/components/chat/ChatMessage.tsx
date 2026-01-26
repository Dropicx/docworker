/**
 * Individual chat message bubble component.
 */

import React from 'react';
import { User, BookOpen, Loader2 } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import ReactMarkdown from 'react-markdown';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          isUser
            ? 'bg-brand-100 text-brand-600'
            : 'bg-accent-100 text-accent-600'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <BookOpen className="w-4 h-4" />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={`flex-1 max-w-[80%] ${
          isUser ? 'flex flex-col items-end' : ''
        }`}
      >
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-brand-600 text-white rounded-tr-sm'
              : 'bg-white border border-neutral-200 text-neutral-800 rounded-tl-sm shadow-sm'
          }`}
        >
          {message.isStreaming && !message.content ? (
            <div className="flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm opacity-70">Antwortet...</span>
            </div>
          ) : isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-neutral prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0.5">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}

          {/* Streaming indicator */}
          {message.isStreaming && message.content && (
            <span className="inline-block w-1.5 h-4 bg-current opacity-70 animate-pulse ml-0.5" />
          )}
        </div>

        {/* Timestamp */}
        <div
          className={`text-xs text-neutral-400 mt-1 px-1 ${
            isUser ? 'text-right' : 'text-left'
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString('de-DE', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
