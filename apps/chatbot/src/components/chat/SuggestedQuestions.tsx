/**
 * Suggested questions component for follow-up prompts.
 * Displays clickable question buttons that send the question to the chat.
 */

import React from 'react';
import { Sparkles } from 'lucide-react';

interface SuggestedQuestionsProps {
  questions: string[];
  onQuestionClick: (question: string) => void;
  isLoading?: boolean;
}

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  questions,
  onQuestionClick,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="px-3 py-2 md:px-4 md:py-3 border-t border-neutral-100 dark:border-neutral-800">
        <div className="flex items-center gap-1.5 md:gap-2 mb-1.5 md:mb-2">
          <Sparkles className="w-3 h-3 md:w-3.5 md:h-3.5 text-accent-500 animate-pulse" />
          <span className="text-[10px] md:text-xs font-medium text-neutral-500 dark:text-neutral-400">
            Lade Vorschlage...
          </span>
        </div>
        <div className="flex flex-wrap gap-1.5 md:gap-2">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-7 md:h-8 w-32 md:w-48 bg-neutral-100 dark:bg-neutral-800 rounded-lg animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  if (!questions || questions.length === 0) {
    return null;
  }

  return (
    <div className="px-3 py-2 md:px-4 md:py-3 border-t border-neutral-100 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-800/30">
      {/* Header */}
      <div className="flex items-center gap-1.5 md:gap-2 mb-1.5 md:mb-2">
        <Sparkles className="w-3 h-3 md:w-3.5 md:h-3.5 text-accent-500" />
        <span className="text-[10px] md:text-xs font-medium text-neutral-500 dark:text-neutral-400">
          Vorgeschlagene Fragen
        </span>
      </div>

      {/* Question buttons */}
      <div className="flex flex-wrap gap-1.5 md:gap-2">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => onQuestionClick(question)}
            className="px-2 py-1.5 md:px-3 md:py-2 text-xs md:text-sm text-left text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 hover:bg-brand-50 dark:hover:bg-brand-900/20 border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-700 rounded-lg transition-all hover:shadow-sm"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedQuestions;
