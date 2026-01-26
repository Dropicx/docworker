/**
 * Individual chat message bubble component.
 */

import React from 'react';
import { User, BookOpen, Loader2 } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
            <div className="prose prose-sm max-w-none prose-neutral
              prose-p:my-3 prose-p:leading-relaxed
              prose-headings:mt-4 prose-headings:mb-2 prose-headings:font-semibold
              prose-h1:text-lg prose-h2:text-base prose-h3:text-sm
              prose-ul:my-3 prose-ul:ml-4 prose-ol:my-3 prose-ol:ml-4
              prose-li:my-1.5 prose-li:leading-relaxed
              prose-strong:text-neutral-900
              prose-code:bg-neutral-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
              prose-blockquote:border-l-brand-500 prose-blockquote:bg-brand-50 prose-blockquote:py-1 prose-blockquote:px-3 prose-blockquote:my-3
              prose-hr:my-4
            ">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
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
