/**
 * Individual chat message bubble component.
 */

import React, { useState, useCallback } from 'react';
import { User, BookOpen, Loader2, Copy, Check } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * Copy button for code blocks.
 */
const CodeCopyButton: React.FC<{ code: string }> = ({ code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 text-neutral-400 hover:text-neutral-600 bg-white/80 hover:bg-white rounded border border-neutral-200 opacity-0 group-hover:opacity-100 transition-opacity"
      title={copied ? 'Kopiert!' : 'Code kopieren'}
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-green-600" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
};

/**
 * Custom code component for ReactMarkdown with syntax highlighting.
 */
const createCodeComponent = (): Components['code'] => {
  return ({ className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '');
    const code = String(children).replace(/\n$/, '');
    const isInline = !match && !code.includes('\n');

    if (isInline) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }

    return (
      <div className="group relative my-3 -mx-1">
        <CodeCopyButton code={code} />
        <SyntaxHighlighter
          style={oneLight}
          language={match?.[1] || 'text'}
          PreTag="div"
          customStyle={{
            margin: 0,
            borderRadius: '0.5rem',
            fontSize: '0.75rem',
            padding: '1rem',
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    );
  };
};

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [message.content]);

  return (
    <div
      className={`group flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
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
        <div className="relative">
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
              prose-pre:p-0 prose-pre:bg-transparent prose-pre:my-0
            ">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code: createCodeComponent(),
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}

            {/* Streaming indicator */}
            {message.isStreaming && message.content && (
              <span className="inline-block w-1.5 h-4 bg-current opacity-70 animate-pulse ml-0.5" />
            )}
          </div>

          {/* Copy button - only for assistant messages with content */}
          {!isUser && message.content && !message.isStreaming && (
            <button
              onClick={handleCopy}
              className="absolute -right-8 top-2 p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded opacity-0 group-hover:opacity-100 transition-opacity"
              title={copied ? 'Kopiert!' : 'Kopieren'}
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-600" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
            </button>
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
