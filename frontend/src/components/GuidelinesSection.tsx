import React from 'react';
import { BookOpen, Clock, AlertTriangle, RefreshCw, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { GuidelinesResponse } from '../types/api';
import ApiService from '../services/api';

interface GuidelinesSectionProps {
  guidelines: GuidelinesResponse | null;
  isLoading: boolean;
  sectionRef: React.RefObject<HTMLDivElement>;
  onRetry?: () => void;
}

const GuidelinesSection: React.FC<GuidelinesSectionProps> = ({
  guidelines,
  isLoading,
  sectionRef,
  onRetry,
}) => {
  // Don't render if not configured
  if (guidelines?.status === 'not_configured') {
    return null;
  }

  // Loading skeleton
  if (isLoading) {
    return (
      <div ref={sectionRef} className="card-elevated border-brand-200/50 animate-pulse">
        <div className="card-body">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-brand-100 rounded-xl" />
            <div className="flex-1">
              <div className="h-6 bg-brand-100 rounded w-64 mb-2" />
              <div className="h-4 bg-brand-50 rounded w-48" />
            </div>
          </div>
          <div className="space-y-3">
            <div className="h-4 bg-neutral-100 rounded w-full" />
            <div className="h-4 bg-neutral-100 rounded w-5/6" />
            <div className="h-4 bg-neutral-100 rounded w-4/6" />
            <div className="h-4 bg-neutral-100 rounded w-full" />
            <div className="h-4 bg-neutral-100 rounded w-3/4" />
          </div>
        </div>
      </div>
    );
  }

  // Error or not available state
  if (guidelines?.status === 'error' || guidelines?.status === 'not_available') {
    return (
      <div
        ref={sectionRef}
        className="card-elevated border-warning-200/50 bg-gradient-to-br from-warning-50/30 to-orange-50/30"
      >
        <div className="card-body">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-gradient-to-br from-warning-400 to-warning-500 rounded-xl flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-warning-900 mb-2">
                Leitlinien-Empfehlungen nicht verfügbar
              </h3>
              <p className="text-warning-700 text-sm mb-4">
                {guidelines?.error_message || 'Die AWMF-Leitlinien konnten nicht abgerufen werden.'}
              </p>
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="btn-secondary text-sm inline-flex items-center space-x-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Erneut versuchen</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // No guidelines data yet
  if (!guidelines || guidelines.status !== 'success' || !guidelines.guidelines_text) {
    return null;
  }

  return (
    <div
      ref={sectionRef}
      className="card-elevated border-brand-200/50 bg-gradient-to-br from-brand-50/30 to-accent-50/30"
    >
      <div className="card-body">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3 sm:space-x-4">
            <div className="w-12 h-12 sm:w-14 sm:h-14 bg-gradient-to-br from-brand-500 via-brand-600 to-accent-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-soft flex-shrink-0">
              <BookOpen className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 text-white" />
            </div>
            <div className="min-w-0">
              <h3 className="text-lg sm:text-xl lg:text-2xl font-bold text-primary-900">
                Leitlinien-Empfehlungen
              </h3>
              <p className="text-xs sm:text-sm lg:text-base text-primary-600">
                Basierend auf AWMF-Richtlinien
              </p>
            </div>
          </div>

          {/* Processing time */}
          {guidelines.processing_time_seconds && (
            <div className="hidden sm:flex items-center space-x-2 text-xs text-primary-500">
              <Clock className="w-3.5 h-3.5" />
              <span>{ApiService.formatDuration(guidelines.processing_time_seconds)}</span>
            </div>
          )}
        </div>

        {/* Guidelines Content */}
        <div className="glass-card p-4 sm:p-6 md:p-8">
          <div className="medical-text-formatted text-primary-800 leading-relaxed markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className="prose prose-sm max-w-none"
              components={{
                h1: ({ children }) => (
                  <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4 mt-6 pb-2 border-b border-gray-200">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-xl sm:text-2xl font-bold text-gray-800 mb-3 mt-6 pb-1 border-b border-gray-100">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-lg sm:text-xl font-semibold text-gray-800 mb-2 mt-4">
                    {children}
                  </h3>
                ),
                h4: ({ children }) => (
                  <h4 className="text-base sm:text-lg font-semibold text-gray-700 mb-2 mt-3">
                    {children}
                  </h4>
                ),
                p: ({ children }) => (
                  <p className="mb-3 text-gray-700 leading-relaxed">{children}</p>
                ),
                ul: ({ children }) => <ul className="list-none pl-0 mb-3 space-y-1">{children}</ul>,
                li: ({ children }) => (
                  <li className="flex items-start text-gray-800 leading-snug py-0.5">
                    <span className="text-brand-500 mr-2 mt-0.5 flex-shrink-0">•</span>
                    <span>{children}</span>
                  </li>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-gray-900">{children}</strong>
                ),
                em: ({ children }) => {
                  // Style citation lines differently (they typically contain source info)
                  const text = String(children);
                  if (
                    text.includes('Quelle:') ||
                    text.includes('AWMF') ||
                    text.includes('Reg.-Nr.')
                  ) {
                    return (
                      <em className="block text-xs sm:text-sm text-primary-500 mt-2 not-italic">
                        {children}
                      </em>
                    );
                  }
                  return <em className="italic text-gray-600">{children}</em>;
                },
                hr: () => <hr className="my-6 border-primary-200" />,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-brand-400 pl-4 py-2 my-4 bg-brand-50/50 rounded-r-lg">
                    {children}
                  </blockquote>
                ),
              }}
            >
              {guidelines.guidelines_text}
            </ReactMarkdown>
          </div>
        </div>

        {/* Metadata / Sources */}
        {guidelines.metadata?.retriever_resources &&
          guidelines.metadata.retriever_resources.length > 0 && (
            <div className="mt-4 pt-4 border-t border-primary-200/50">
              <div className="flex items-center space-x-2 text-xs text-primary-500 mb-2">
                <FileText className="w-3.5 h-3.5" />
                <span className="font-medium">Verwendete Quellen</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {guidelines.metadata.retriever_resources.slice(0, 5).map((resource, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-1 bg-primary-50 text-primary-600 rounded text-xs"
                    title={`Score: ${resource.score?.toFixed(2) || 'N/A'}`}
                  >
                    {resource.document_name || `Dokument ${idx + 1}`}
                  </span>
                ))}
              </div>
            </div>
          )}

        {/* Disclaimer */}
        <div className="mt-6 p-4 bg-warning-50/50 rounded-lg border border-warning-200/50">
          <p className="text-xs sm:text-sm text-warning-700">
            <strong>Hinweis:</strong> Diese Empfehlungen basieren auf offiziellen deutschen
            Behandlungsrichtlinien (AWMF) und dienen nur zur Information. Sie ersetzen nicht das
            persönliche Gespräch mit Ihrem Arzt.
          </p>
        </div>
      </div>
    </div>
  );
};

export default GuidelinesSection;
