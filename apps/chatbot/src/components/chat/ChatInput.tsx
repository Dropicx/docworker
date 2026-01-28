/**
 * Chat input component with textarea and send button.
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, StopCircle, X } from 'lucide-react';

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
  const [showDisclaimer, setShowDisclaimer] = useState(() => {
    return localStorage.getItem('hideAiDisclaimer') !== 'true';
  });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleDismissDisclaimer = () => {
    setShowDisclaimer(false);
    localStorage.setItem('hideAiDisclaimer', 'true');
  };

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
    <form onSubmit={handleSubmit} className="flex-shrink-0 border-t border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-2 pt-2 pb-2 md:px-4 md:pt-4 md:pb-3">
      <div className="flex items-center gap-2 md:gap-3">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full px-3 py-2.5 md:px-4 md:py-3 text-sm md:text-base border border-neutral-200 dark:border-neutral-700 rounded-xl resize-none bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 focus:border-brand-500 dark:focus:border-brand-400 focus:ring-2 focus:ring-brand-100 dark:focus:ring-brand-900/30 focus:outline-none transition-colors disabled:bg-neutral-50 dark:disabled:bg-neutral-800 disabled:text-neutral-400 dark:disabled:text-neutral-500"
            style={{ minHeight: '40px', maxHeight: '120px' }}
          />
        </div>

        {disabled && onStop ? (
          <button
            type="button"
            onClick={onStop}
            className="flex-shrink-0 p-2.5 md:p-3 bg-error-600 text-white rounded-xl hover:bg-error-700 transition-colors self-center"
            title="Generierung stoppen"
          >
            <StopCircle className="w-5 h-5" />
          </button>
        ) : (
          <button
            type="submit"
            disabled={disabled || !message.trim()}
            className="flex-shrink-0 p-2.5 md:p-3 bg-brand-600 text-white rounded-xl hover:bg-brand-700 disabled:bg-neutral-200 dark:disabled:bg-neutral-700 disabled:text-neutral-400 dark:disabled:text-neutral-500 disabled:cursor-not-allowed transition-colors self-center"
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

      {/* Character count - desktop only, hint hidden on mobile */}
      <div className="hidden md:flex justify-between items-center mt-2 px-1">
        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          Enter zum Senden, Shift+Enter fur neue Zeile
        </p>
        <p className={`text-xs ${message.length > maxLength * 0.9 ? 'text-amber-600 dark:text-amber-400 font-medium' : 'text-neutral-400 dark:text-neutral-500'}`}>
          {message.length.toLocaleString('de-DE')} / {maxLength.toLocaleString('de-DE')} Zeichen
        </p>
      </div>

      {/* AI Disclaimer - dismissable, shorter on mobile */}
      {showDisclaimer && (
        <div className="mt-2 md:mt-3 pt-2 md:pt-3 border-t border-neutral-100 dark:border-neutral-800 relative">
          <button
            type="button"
            onClick={handleDismissDisclaimer}
            className="absolute -top-1 right-0 p-1 text-neutral-300 dark:text-neutral-600 hover:text-neutral-500 dark:hover:text-neutral-400 transition-colors"
            title="Hinweis ausblenden"
          >
            <X className="w-3.5 h-3.5" />
          </button>
          {/* Short version on mobile */}
          <p className="md:hidden text-[10px] text-neutral-400 dark:text-neutral-500 text-center leading-relaxed pr-4">
            <span className="font-medium text-amber-600 dark:text-amber-400">KI-Assistent</span> - keine arztliche Beratung
          </p>
          {/* Full version on desktop */}
          <p className="hidden md:block text-[10px] text-neutral-400 dark:text-neutral-500 text-center leading-relaxed pr-4">
            <span className="font-medium text-amber-600 dark:text-amber-400">Hinweis:</span> Dies ist ein KI-Assistent, kein Arzt.
            Die Antworten basieren auf Leitlinien, ersetzen aber keine arztliche Beratung.
            Bei gesundheitlichen Beschwerden wenden Sie sich an medizinisches Fachpersonal.
          </p>
        </div>
      )}
    </form>
  );
};

export default ChatInput;
