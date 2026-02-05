import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Upload, ChevronDown, ChevronUp } from 'lucide-react';

interface TerminationCardProps {
  message: string;
  reason?: string;
  step?: string;
  onReset: () => void;
}

/**
 * TerminationCard Component
 *
 * Displays a user-friendly message when pipeline processing is terminated
 * due to business rules (e.g., non-medical content, unsupported document type).
 *
 * This is distinct from error states which indicate system failures.
 * Termination is a graceful, expected outcome for certain inputs.
 */
const TerminationCard: React.FC<TerminationCardProps> = ({ message, reason, step, onReset }) => {
  const { t } = useTranslation();
  const [showDetails, setShowDetails] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);

  // Focus management for accessibility
  useEffect(() => {
    cardRef.current?.focus();
  }, []);

  return (
    <div
      ref={cardRef}
      className="min-h-screen flex items-center justify-center p-4 animate-fade-in"
      tabIndex={-1}
    >
      <div className="max-w-2xl w-full">
        <div
          className="card-elevated border-warning-200/50 bg-gradient-to-br from-warning-50/50 to-white"
          role="alert"
          aria-live="polite"
          aria-atomic="true"
        >
          <div className="card-body">
            {/* Icon and Title */}
            <div className="flex items-start space-x-4 mb-6">
              <div className="flex-shrink-0 w-12 h-12 sm:w-14 sm:h-14 bg-gradient-to-br from-warning-500 to-warning-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-soft">
                <AlertCircle className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
              </div>

              <div className="flex-1 min-w-0">
                <h3 className="text-xl sm:text-2xl font-bold text-warning-900 mb-2">
                  {t('termination.title')}
                </h3>
                <p className="text-warning-800 text-base sm:text-lg leading-relaxed">{message}</p>
              </div>
            </div>

            {/* Technical Details (Collapsible) */}
            {(reason || step) && (
              <div className="mb-6">
                <button
                  onClick={() => setShowDetails(!showDetails)}
                  className="flex items-center space-x-2 text-sm text-warning-700 hover:text-warning-800 font-medium transition-colors"
                  aria-expanded={showDetails}
                  aria-controls="technical-details"
                >
                  <span>{t('termination.technicalDetails')}</span>
                  {showDetails ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {showDetails && (
                  <div
                    id="technical-details"
                    className="mt-3 p-4 bg-warning-50 border border-warning-200 rounded-lg animate-slide-down"
                  >
                    <dl className="space-y-2 text-sm">
                      {step && (
                        <div>
                          <dt className="font-semibold text-warning-900">{t('termination.step')}</dt>
                          <dd className="text-warning-700 ml-4">{step}</dd>
                        </div>
                      )}
                      {reason && (
                        <div>
                          <dt className="font-semibold text-warning-900">{t('termination.reason')}</dt>
                          <dd className="text-warning-700 ml-4">{reason}</dd>
                        </div>
                      )}
                    </dl>
                  </div>
                )}
              </div>
            )}

            {/* Call to Action */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={onReset}
                className="btn-primary group flex-1 sm:flex-initial"
                aria-label={t('termination.uploadNew')}
              >
                <Upload className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
                <span>{t('termination.uploadNew')}</span>
              </button>
            </div>

            {/* Helpful Tips */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="text-sm font-semibold text-blue-900 mb-2">💡 {t('termination.hint')}</h4>
              <p className="text-sm text-blue-800 leading-relaxed">
                {t('termination.hintText')}
              </p>
              <ul className="mt-2 space-y-1 text-sm text-blue-700">
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>{t('termination.doctorLetters')}</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>{t('termination.reports')}</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>{t('termination.labResults')}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TerminationCard;
