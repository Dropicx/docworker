import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Clock,
  CheckCircle,
  AlertCircle,
  Loader,
  RefreshCw,
  X,
  Sparkles,
  Zap,
  FileCheck,
} from 'lucide-react';
import ApiService from '../services/api';
import { ProcessingProgress, ProcessingStatus as Status } from '../types/api';
import { isTerminated, getTerminationMetadata } from '../utils/termination';

interface ProcessingStatusProps {
  processingId: string;
  onComplete: () => void;
  onError: (error: string, metadata?: Record<string, unknown>) => void;
  onCancel?: () => void;
}

const STEPS = [
  { label: 'Text extrahieren (OCR)', threshold: 15, status: 'extracting_text' as Status },
  { label: 'Medizinische Validierung', threshold: 30, status: 'extracting_text' as Status },
  { label: 'Datenschutz-Filter', threshold: 48, status: 'translating' as Status },
  { label: 'KI-Vereinfachung', threshold: 65, status: 'translating' as Status },
  { label: 'Qualitätsprüfung', threshold: 82, status: 'language_translating' as Status },
  { label: 'Finalisierung', threshold: 95, status: 'language_translating' as Status },
];

const STEP_MESSAGES: Record<string, string[]> = {
  extracting_text: [
    'Dokument wird gescannt...',
    'Zeichen werden erkannt...',
    'Textstruktur wird analysiert...',
  ],
  translating: [
    'Medizinische Fachbegriffe werden erkannt...',
    'Text wird in einfache Sprache übersetzt...',
    'Zusammenhänge werden geprüft...',
  ],
  language_translating: [
    'Übersetzung wird optimiert...',
    'Grammatik wird geprüft...',
    'Formatierung wird angepasst...',
  ],
};

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({
  processingId,
  onComplete,
  onError,
  onCancel,
}) => {
  const [status, setStatus] = useState<ProcessingProgress | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [displayedProgress, setDisplayedProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [rotatingMessageIndex, setRotatingMessageIndex] = useState(0);

  const startTimeRef = useRef(Date.now());
  const targetProgressRef = useRef(0);
  const animationFrameRef = useRef<number | null>(null);
  const lastUpdateTimeRef = useRef(Date.now());
  const lastProgressValueRef = useRef(0);

  // Elapsed time counter
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Rotating messages every 4 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      setRotatingMessageIndex((prev) => prev + 1);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  // Smooth progress animation with aggressive creep for long-running steps
  const animateProgress = useCallback(() => {
    setDisplayedProgress((current) => {
      const target = targetProgressRef.current;

      // Phase 1: Animate toward target when backend reports new progress
      if (current < target) {
        const step = Math.max(0.3, (target - current) * 0.08);
        return Math.min(current + step, target);
      }

      // Phase 2: Creep forward during long gaps between backend updates
      // The backend only updates at step boundaries, so steps like OCR/Translation
      // can run 30-90s with no progress change. We creep to keep the UI alive.
      const now = Date.now();
      const timeSinceUpdate = now - lastUpdateTimeRef.current;

      if (timeSinceUpdate > 2000 && current < 95 && current >= target) {
        // Allow creeping up to target + 28%, capped at 95%
        const maxCreep = Math.min(target + 28, 95);
        if (current < maxCreep) {
          // Deceleration: creep fast initially, slow down near the cap
          const distanceToMax = maxCreep - current;
          const rate = Math.max(0.005, distanceToMax * 0.0015);
          return current + rate;
        }
      }

      return current;
    });
    animationFrameRef.current = requestAnimationFrame(animateProgress);
  }, []);

  useEffect(() => {
    animationFrameRef.current = requestAnimationFrame(animateProgress);
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [animateProgress]);

  // Update target only when progress value actually changes
  useEffect(() => {
    if (status) {
      const newProgress = status.status === 'completed' ? 100 : status.progress_percent;
      if (newProgress !== lastProgressValueRef.current) {
        lastProgressValueRef.current = newProgress;
        targetProgressRef.current = newProgress;
        lastUpdateTimeRef.current = Date.now();
      }
    }
  }, [status]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const statusResponse = await ApiService.getProcessingStatus(processingId);
        setStatus(statusResponse);

        if (statusResponse.status === 'completed') {
          setIsPolling(false);
          setTimeout(onComplete, 1500);
        } else if (statusResponse.status === 'error') {
          setIsPolling(false);
          setError(statusResponse.error || 'Unbekannter Fehler');
          onError(statusResponse.error || 'Verarbeitung fehlgeschlagen');
        } else if (isTerminated(statusResponse)) {
          setIsPolling(false);
          const metadata = getTerminationMetadata(statusResponse);
          setError(metadata.message);
          onError(metadata.message, metadata as unknown as Record<string, unknown>);
        }
      } catch (err) {
        console.error('Status polling error:', err as Error);
        setError((err as Error).message);
        setIsPolling(false);
        onError((err as Error).message);
      }
    };

    if (isPolling) {
      pollStatus();
      intervalId = setInterval(pollStatus, 2000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [processingId, isPolling, onComplete, onError]);

  const handleCancel = async () => {
    try {
      await ApiService.cancelProcessing(processingId);
      setIsPolling(false);
      onCancel?.();
    } catch (err) {
      console.error('Cancel error:', err as Error);
      setError((err as Error).message);
    }
  };

  const formatElapsedTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds} Sek.`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins} Min. ${secs} Sek.`;
  };

  const getActiveStatus = (): Status => {
    return status?.status || 'pending';
  };

  const getCurrentMessages = (): string[] => {
    const currentStatus = getActiveStatus();
    return STEP_MESSAGES[currentStatus] || STEP_MESSAGES['extracting_text'];
  };

  const getRotatingMessage = (): string => {
    const messages = getCurrentMessages();
    return messages[rotatingMessageIndex % messages.length];
  };

  const getStatusIcon = (s: Status) => {
    switch (s) {
      case 'pending':
        return <Clock className="w-5 h-5 text-warning-600" />;
      case 'processing':
      case 'extracting_text':
      case 'translating':
      case 'language_translating':
        return <Loader className="w-5 h-5 text-brand-600 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-success-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-600" />;
      case 'non_medical_content':
      case 'terminated':
        return <AlertCircle className="w-5 h-5 text-warning-600" />;
      default:
        return <RefreshCw className="w-5 h-5 text-primary-600" />;
    }
  };

  const getProgressColor = (s: Status) => {
    switch (s) {
      case 'completed':
        return 'from-success-500 via-success-600 to-success-700';
      case 'error':
        return 'from-error-500 via-error-600 to-error-700';
      default:
        return 'from-brand-500 via-brand-600 to-accent-600';
    }
  };

  const isStepCompleted = (threshold: number): boolean => {
    return displayedProgress >= threshold;
  };

  const isStepActive = (index: number): boolean => {
    const threshold = STEPS[index].threshold;
    const prevThreshold = index > 0 ? STEPS[index - 1].threshold : 0;
    return displayedProgress >= prevThreshold && displayedProgress < threshold;
  };

  if (!status) {
    return (
      <div className="card-elevated animate-scale-in">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <div className="relative">
              <div className="w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl flex items-center justify-center animate-pulse-soft">
                <Loader className="w-8 h-8 text-white animate-spin" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-gradient-to-br from-accent-500 to-accent-600 rounded-full flex items-center justify-center animate-pulse-soft">
                <div className="w-2 h-2 bg-white rounded-full"></div>
              </div>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-primary-900 mb-1">Status wird geladen</h3>
              <p className="text-primary-600 text-sm">Verbindung zum Verarbeitungsserver...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card-elevated animate-scale-in">
      <div className="card-body">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 sm:mb-8 space-y-3 sm:space-y-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl sm:rounded-2xl flex items-center justify-center flex-shrink-0">
              {status.status === 'completed' ? (
                <Sparkles className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              ) : (
                <Zap className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
              )}
            </div>
            <div className="min-w-0">
              <h3 className="text-lg sm:text-xl font-bold text-primary-900">KI-Verarbeitung</h3>
              <p className="text-xs sm:text-sm text-primary-600">
                Ihr Dokument wird analysiert und übersetzt
              </p>
            </div>
          </div>

          {(status.status === 'pending' ||
            status.status === 'processing' ||
            status.status === 'extracting_text' ||
            status.status === 'translating' ||
            status.status === 'language_translating') &&
            onCancel && (
              <button
                onClick={handleCancel}
                className="p-2 text-primary-400 hover:text-primary-600 hover:bg-primary-50 rounded-xl transition-all duration-200"
                title="Verarbeitung abbrechen"
              >
                <X className="w-5 h-5" />
              </button>
            )}
        </div>

        {/* Status Display */}
        <div className="space-y-4 sm:space-y-6">
          {/* Current Status */}
          <div className="glass-effect p-4 sm:p-6 rounded-xl sm:rounded-2xl">
            <div className="flex items-center space-x-3 mb-4">
              {getStatusIcon(status.status)}
              <span className={`status-badge ${ApiService.getStatusColor(status.status)}`}>
                {ApiService.getStatusText(status.status)}
              </span>
              {/* Activity pulse indicator */}
              {status.status !== 'completed' && status.status !== 'error' && (
                <div className="flex items-center text-xs text-brand-600">
                  <div className="w-2 h-2 bg-brand-500 rounded-full mr-2 animate-pulse"></div>
                  Aktiv
                </div>
              )}
              {status.status === 'completed' && (
                <div className="flex items-center text-xs text-success-600">
                  <div className="w-2 h-2 bg-success-500 rounded-full mr-2 animate-pulse-soft"></div>
                  Abgeschlossen
                </div>
              )}
              {status.status === 'non_medical_content' && (
                <div className="flex items-center text-xs text-error-600">
                  <div className="w-2 h-2 bg-error-500 rounded-full mr-2"></div>
                  Nicht-medizinisch
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-primary-700">Fortschritt</span>
                <div className="flex items-center space-x-2">
                  {/* Pulsing dot next to percentage */}
                  {status.status !== 'completed' && status.status !== 'error' && (
                    <div className="w-1.5 h-1.5 bg-brand-500 rounded-full animate-pulse"></div>
                  )}
                  <span className="font-bold text-primary-900">
                    {Math.round(displayedProgress)}%
                  </span>
                </div>
              </div>

              <div className="progress-bar h-3">
                <div
                  className={`progress-fill bg-gradient-to-r ${getProgressColor(status.status)} transition-none`}
                  style={{ width: `${displayedProgress}%` }}
                />
              </div>

              {/* Step description from backend */}
              <p className="text-sm text-primary-600 leading-relaxed">{status.current_step}</p>

              {/* Elapsed time */}
              {status.status !== 'completed' && status.status !== 'error' && (
                <p className="text-xs text-primary-500">
                  Verarbeitung läuft seit {formatElapsedTime(elapsedSeconds)}
                </p>
              )}
            </div>
          </div>

          {/* Processing Steps */}
          <div className="space-y-3 sm:space-y-4">
            <h4 className="text-base sm:text-lg font-semibold text-primary-900 flex items-center">
              <FileCheck className="w-4 h-4 sm:w-5 sm:h-5 mr-2 text-brand-600" />
              Verarbeitungsschritte
            </h4>

            <div className="space-y-2 sm:space-y-3">
              {STEPS.map((item, index) => {
                const completed = isStepCompleted(item.threshold);
                const active = isStepActive(index);
                return (
                  <div
                    key={index}
                    className={`flex items-center space-x-3 sm:space-x-4 p-3 sm:p-4 rounded-lg sm:rounded-xl transition-all duration-300 ${
                      completed
                        ? 'bg-gradient-to-r from-success-50 to-success-50/50 border border-success-200'
                        : active
                          ? 'bg-gradient-to-r from-brand-50 to-accent-50/50 border border-brand-200'
                          : 'bg-neutral-50 border border-neutral-200'
                    }`}
                  >
                    <div
                      className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl flex items-center justify-center transition-all duration-300 flex-shrink-0 ${
                        completed
                          ? 'bg-gradient-to-br from-success-500 to-success-600'
                          : active
                            ? 'bg-gradient-to-br from-brand-500 to-brand-600'
                            : 'bg-neutral-200'
                      }`}
                    >
                      {completed ? (
                        <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                      ) : active ? (
                        <Loader className="w-4 h-4 sm:w-5 sm:h-5 text-white animate-spin" />
                      ) : (
                        <div className="w-2 h-2 bg-neutral-400 rounded-full"></div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div
                        className={`text-sm sm:text-base font-medium truncate ${
                          completed
                            ? 'text-success-900'
                            : active
                              ? 'text-brand-900'
                              : 'text-neutral-600'
                        }`}
                      >
                        {item.label}
                      </div>
                      {/* Rotating sub-message for active step */}
                      {active && (
                        <p className="text-xs text-brand-600 mt-0.5 animate-pulse-soft truncate">
                          {getRotatingMessage()}
                        </p>
                      )}
                    </div>
                    {completed && (
                      <div className="w-6 h-6 bg-success-100 rounded-full flex items-center justify-center">
                        <CheckCircle className="w-4 h-4 text-success-600" />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Messages */}
          {error && (
            <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white">
              <div className="card-compact">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
                    <AlertCircle className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-error-900 mb-1">
                      Verarbeitung fehlgeschlagen
                    </h4>
                    <p className="text-error-700 text-sm leading-relaxed">{error}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {status.message && !error && (
            <div className="glass-effect p-4 rounded-xl border border-brand-200/50">
              <div className="text-brand-700 text-sm leading-relaxed">{status.message}</div>
            </div>
          )}

          {status.status === 'completed' && (
            <div className="card-elevated border-success-200/50 bg-gradient-to-br from-success-50/50 to-white">
              <div className="card-compact">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-success-500 to-success-600 rounded-xl flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-success-900 mb-1">
                      Übersetzung abgeschlossen!
                    </h4>
                    <p className="text-success-700 text-sm leading-relaxed">
                      Ihr Dokument wurde erfolgreich in verständliche Sprache übersetzt. Das
                      Ergebnis wird geladen...
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {status.status === 'non_medical_content' && (
            <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white">
              <div className="card-compact">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
                    <FileCheck className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-error-900 mb-1">
                      Nicht-medizinischer Inhalt erkannt
                    </h4>
                    <p className="text-error-700 text-sm leading-relaxed mb-3">
                      {status.error ||
                        'Dieses Dokument scheint keinen medizinischen Inhalt zu enthalten.'}
                    </p>
                    <div className="bg-error-100 border border-error-200 rounded-lg p-3">
                      <p className="text-error-800 text-xs font-medium mb-1">
                        Bitte laden Sie eines der folgenden Dokumente hoch:
                      </p>
                      <ul className="text-error-700 text-xs space-y-1">
                        <li>• Arztbriefe und Entlassungsbriefe</li>
                        <li>• Laborwerte und Blutbefunde</li>
                        <li>• Medizinische Befunde und Berichte</li>
                        <li>• Überweisungen und Konsiliarbriefe</li>
                        <li>• Röntgen- und MRT-Befunde</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Processing ID */}
          <div className="text-center">
            <p className="text-xs text-primary-500">
              Verarbeitungs-ID: <span className="font-mono">{status.processing_id}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProcessingStatus;
