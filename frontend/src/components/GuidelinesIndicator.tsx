import React from 'react';
import { Loader2, ChevronDown, AlertCircle, BookOpen } from 'lucide-react';

interface GuidelinesIndicatorProps {
  status: 'idle' | 'loading' | 'success' | 'error' | 'not_available' | 'not_configured';
  onScrollToGuidelines: () => void;
  errorMessage?: string;
}

const GuidelinesIndicator: React.FC<GuidelinesIndicatorProps> = ({
  status,
  onScrollToGuidelines,
  errorMessage,
}) => {
  // Don't show anything if not configured
  if (status === 'not_configured' || status === 'idle') {
    return null;
  }

  const getStatusContent = () => {
    switch (status) {
      case 'loading':
        return (
          <div className="flex items-center space-x-2 sm:space-x-3 text-brand-600">
            <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
            <span className="hidden sm:inline text-sm font-medium">
              Leitlinien werden geladen...
            </span>
            <span className="sm:hidden text-xs font-medium">Laden...</span>
          </div>
        );

      case 'success':
        return (
          <button
            onClick={onScrollToGuidelines}
            className="flex items-center space-x-2 sm:space-x-3 text-brand-700 hover:text-brand-800 transition-colors group"
          >
            <BookOpen className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="hidden sm:inline text-sm font-medium group-hover:underline">
              Zu den Leitlinien-Empfehlungen
            </span>
            <span className="sm:hidden text-xs font-medium">Leitlinien</span>
            <ChevronDown className="w-4 h-4 sm:w-5 sm:h-5 animate-bounce" />
          </button>
        );

      case 'error':
      case 'not_available':
        return (
          <div
            className="flex items-center space-x-2 text-warning-600"
            title={errorMessage || 'Leitlinien nicht verfügbar'}
          >
            <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="hidden sm:inline text-xs">Leitlinien nicht verfügbar</span>
          </div>
        );

      default:
        return null;
    }
  };

  const content = getStatusContent();
  if (!content) return null;

  return (
    <div
      className={`
        sticky top-4 z-10 float-right ml-4 mb-4
        px-3 py-2 sm:px-4 sm:py-2.5
        rounded-lg sm:rounded-xl
        backdrop-blur-sm
        border
        transition-all duration-300
        ${
          status === 'loading'
            ? 'bg-brand-50/80 border-brand-200 animate-pulse'
            : status === 'success'
              ? 'bg-gradient-to-r from-brand-50/90 to-accent-50/90 border-brand-300 shadow-soft hover:shadow-md cursor-pointer'
              : 'bg-warning-50/80 border-warning-200'
        }
      `}
    >
      {content}
    </div>
  );
};

export default GuidelinesIndicator;
