/**
 * Individual chat message bubble component.
 */

import React, { useState } from 'react';
import { User, BookOpen, Loader2, Copy, Check } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight, oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../contexts/ThemeContext';
import { MessageActions } from './MessageActions';
import { CitationsDisplay } from './CitationsDisplay';

interface ChatMessageProps {
  message: ChatMessageType;
  conversationId?: string;
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
      className="absolute top-2 right-2 p-1.5 text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 bg-white/80 dark:bg-neutral-800/80 hover:bg-white dark:hover:bg-neutral-700 rounded border border-neutral-200 dark:border-neutral-600 opacity-0 group-hover:opacity-100 transition-opacity"
      title={copied ? 'Kopiert!' : 'Code kopieren'}
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
      ) : (
        <Copy className="w-3.5 h-3.5" />
      )}
    </button>
  );
};

/**
 * Custom code component for ReactMarkdown with syntax highlighting.
 */
const createCodeComponent = (isDark: boolean): Components['code'] => {
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
          style={isDark ? oneDark : oneLight}
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

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, conversationId }) => {
  const isUser = message.role === 'user';
  const { theme } = useTheme();

  return (
    <div
      className={`group flex gap-2 md:gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar - hidden on mobile for assistant, smaller gap */}
      <div
        className={`flex-shrink-0 w-7 h-7 md:w-8 md:h-8 rounded-lg flex items-center justify-center ${
          isUser
            ? 'bg-brand-100 dark:bg-brand-900/30 text-brand-600 dark:text-brand-400'
            : 'hidden md:flex bg-accent-100 dark:bg-accent-900/30 text-accent-600 dark:text-accent-400'
        }`}
      >
        {isUser ? (
          <User className="w-3.5 h-3.5 md:w-4 md:h-4" />
        ) : (
          <BookOpen className="w-3.5 h-3.5 md:w-4 md:h-4" />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={`flex-1 max-w-full md:max-w-[85%] ${
          isUser ? 'flex flex-col items-end' : ''
        }`}
      >
        <div className="relative">
          <div
            className={`rounded-2xl px-3 py-2.5 md:px-4 md:py-3 ${
              isUser
                ? 'bg-brand-600 text-white rounded-tr-sm'
                : 'bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-100 rounded-tl-sm shadow-sm dark:shadow-none'
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
            <>
              <div className="prose prose-sm max-w-none prose-neutral dark:prose-invert
                prose-p:my-2 prose-p:leading-relaxed
                prose-headings:mt-5 prose-headings:mb-2 prose-headings:font-semibold
                prose-h1:text-xl prose-h2:text-lg prose-h3:text-base
                prose-ul:my-1 prose-ul:ml-5 prose-ol:my-1 prose-ol:ml-5
                prose-li:my-0 prose-li:leading-relaxed
                prose-strong:text-neutral-900 dark:prose-strong:text-neutral-100
                prose-code:bg-neutral-100 dark:prose-code:bg-neutral-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
                prose-blockquote:border-l-brand-500 prose-blockquote:bg-brand-50 dark:prose-blockquote:bg-brand-900/20 prose-blockquote:py-2 prose-blockquote:px-4 prose-blockquote:my-3
                prose-hr:my-4
                prose-pre:p-0 prose-pre:bg-transparent prose-pre:my-2
              ">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw]}
                  components={{
                    code: createCodeComponent(theme === 'dark'),
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>

              {/* Citations - only show when message is complete */}
              {!message.isStreaming && message.retrieverResources && message.retrieverResources.length > 0 && (
                <CitationsDisplay resources={message.retrieverResources} />
              )}
            </>
          )}

            {/* Streaming indicator */}
            {message.isStreaming && message.content && (
              <span className="inline-block w-1.5 h-4 bg-current opacity-70 animate-pulse ml-0.5" />
            )}
          </div>

        </div>

        {/* Message Actions (like/dislike/copy) - only for assistant messages */}
        {!isUser && message.content && !message.isStreaming && (
          <div className="flex items-center justify-between mt-1 px-1">
            <MessageActions
              messageId={message.id}
              conversationId={conversationId}
              content={message.content}
            />
            <div className="text-xs text-neutral-400 dark:text-neutral-500">
              {new Date(message.timestamp).toLocaleTimeString('de-DE', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          </div>
        )}

        {/* Timestamp for user messages */}
        {isUser && (
          <div className="text-xs text-neutral-400 dark:text-neutral-500 mt-1 px-1 text-right">
            {new Date(message.timestamp).toLocaleTimeString('de-DE', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
