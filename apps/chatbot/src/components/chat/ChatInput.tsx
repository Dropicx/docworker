/**
 * Chat input component with textarea and send button.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, StopCircle } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  disabled?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  onStop,
  disabled = false,
  placeholder = 'Stellen Sie eine Frage zu medizinischen Leitlinien...',
  maxLength = 2000,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [message]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = message.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setMessage('');
      // Reset height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex-shrink-0 border-t border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-4 pt-4 pb-3">
      <div className="flex items-center gap-3">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full px-4 py-3 border border-neutral-200 dark:border-neutral-700 rounded-xl resize-none bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:focus:ring-brand-900/30 focus:outline-none transition-colors disabled:bg-neutral-50 dark:disabled:bg-neutral-800 disabled:text-neutral-400 dark:disabled:text-neutral-500"
            style={{ minHeight: '48px', maxHeight: '150px' }}
          />
        </div>

        {disabled && onStop ? (
          <button
            type="button"
            onClick={onStop}
            className="flex-shrink-0 p-3 bg-error-600 text-white rounded-xl hover:bg-error-700 transition-colors self-center"
            title="Generierung stoppen"
          >
            <StopCircle className="w-5 h-5" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled || !message.trim()}
            className="flex-shrink-0 p-3 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:bg-neutral-200 dark:disabled:bg-neutral-700 disabled:text-neutral-400 dark:disabled:text-neutral-500 disabled:cursor-not-allowed transition-colors self-center"
            title="Nachricht senden"
          >
            {disabled ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        )}
      </div>

      {/* Character count and hint */}
      <div className="flex justify-between items-center mt-2 px-1">
        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          Enter zum Senden, Shift+Enter fur neue Zeile
        </p>
        <p className={`text-xs ${message.length > maxLength * 0.9 ? 'text-amber-600 dark:text-amber-400 font-medium' : 'text-neutral-400 dark:text-neutral-500'}`}>
          {message.length.toLocaleString('de-DE')} / {maxLength.toLocaleString('de-DE')} Zeichen
        </p>
      </div>

      {/* AI Disclaimer */}
      <div className="mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
        <p className="text-[10px] text-neutral-400 dark:text-neutral-500 text-center leading-relaxed">
          <span className="font-medium text-amber-600 dark:text-amber-400">Hinweis:</span> Dies ist ein KI-Assistent, kein Arzt.
          Die Antworten basieren auf Leitlinien, ersetzen aber keine ärztliche Beratung.
          Bei gesundheitlichen Beschwerden wenden Sie sich an medizinisches Fachpersonal.
        </p>
      </div>
    </form>
  );
};

export default ChatInput;
