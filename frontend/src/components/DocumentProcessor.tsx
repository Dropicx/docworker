import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Upload,
  CheckCircle,
  AlertCircle,
  Loader,
  X,
  Sparkles,
  Zap,
  FileCheck,
  FileText,
  Image,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import ApiService from '../services/api';
import {
  ProcessingProgress,
  ProcessingStatus as Status,
  ProcessingOptions,
  QualityGateErrorDetails,
  ApiError,
} from '../types/api';
import { isTerminated, getTerminationMetadata } from '../utils/termination';

type Phase = 'uploading' | 'initializing' | 'processing' | 'complete';

interface DocumentProcessorProps {
  file: File;
  selectedLanguage: string | null;
  onComplete: (processingId: string) => void;
  onError: (error: string, metadata?: Record<string, unknown>) => void;
  onCancel: () => void;
  onQualityGateError: (error: QualityGateErrorDetails) => void;
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

const STAGE_TO_CARD: Record<string, number> = {
  ocr: 0,
  validation: 1,
  classification: 2,
  translation: 3,
  quality: 4,
  formatting: 5,
};

const DocumentProcessor: React.FC<DocumentProcessorProps> = ({
  file,
  selectedLanguage,
  onComplete,
  onError,
  onCancel,
  onQualityGateError,
}) => {
  const [phase, setPhase] = useState<Phase>('uploading');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [status, setStatus] = useState<ProcessingProgress | null>(null);
  const [displayedProgress, setDisplayedProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [rotatingMessageIndex, setRotatingMessageIndex] = useState(0);

  const startTimeRef = useRef(Date.now());
  const targetProgressRef = useRef(0);
  const animationFrameRef = useRef<number | null>(null);
  const lastUpdateTimeRef = useRef(Date.now());
  const lastProgressValueRef = useRef(0);
  const isPollingRef = useRef(false);
  const processingIdRef = useRef<string | null>(null);

  // Keep processingIdRef in sync
  useEffect(() => {
    processingIdRef.current = processingId;
  }, [processingId]);

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
      setRotatingMessageIndex(prev => prev + 1);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  // Smooth progress animation (same logic as ProcessingStatus)
  const animateProgress = useCallback(() => {
    if (phase !== 'processing') {
      animationFrameRef.current = requestAnimationFrame(animateProgress);
      return;
    }
    setDisplayedProgress(current => {
      const target = targetProgressRef.current;
      if (current < target) {
        const step = Math.max(0.3, (target - current) * 0.08);
        return Math.min(current + step, target);
      }
      const now = Date.now();
      const timeSinceUpdate = now - lastUpdateTimeRef.current;
      if (timeSinceUpdate > 2000 && current < 95 && current >= target) {
        const maxCreep = Math.min(target + 28, 95);
        if (current < maxCreep) {
          const distanceToMax = maxCreep - current;
          const rate = Math.max(0.005, distanceToMax * 0.0015);
          return current + rate;
        }
      }
      return current;
    });
    animationFrameRef.current = requestAnimationFrame(animateProgress);
  }, [phase]);

  useEffect(() => {
    animationFrameRef.current = requestAnimationFrame(animateProgress);
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [animateProgress]);

  // Update target when status progress changes
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

  // Phase 1: Upload the file
  useEffect(() => {
    let cancelled = false;

    const doUpload = async () => {
      try {
        const response = await ApiService.uploadDocument(file, percent => {
          if (!cancelled) setUploadProgress(percent);
        });

        if (cancelled) return;

        setProcessingId(response.processing_id);
        setUploadProgress(100);
        setPhase('initializing');

        // Start processing
        const options: ProcessingOptions = {};
        if (selectedLanguage) {
          options.target_language = selectedLanguage;
        }

        await ApiService.startProcessing(response.processing_id, options);
        if (cancelled) return;

        setPhase('processing');
        isPollingRef.current = true;
      } catch (error) {
        if (cancelled) return;

        // Check if this is a quality gate error
        if (error instanceof ApiError && error.isQualityGateError()) {
          const qualityDetails = error.getQualityGateDetails();
          if (qualityDetails) {
            onQualityGateError(qualityDetails);
            return;
          }
        }

        const errorMessage = (error as Error).message || 'Upload fehlgeschlagen';
        if (errorMessage.includes('timeout')) {
          onError(
            'Die Verbindung zum Server dauert länger als erwartet. Bitte überprüfen Sie Ihre Internetverbindung und versuchen Sie es erneut.'
          );
        } else {
          onError(errorMessage);
        }
      }
    };

    doUpload();
    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Phase 3: Poll processing status
  useEffect(() => {
    if (phase !== 'processing' || !processingId) return;

    const pollStatus = async () => {
      if (!isPollingRef.current) return;
      try {
        const statusResponse = await ApiService.getProcessingStatus(processingId);
        setStatus(statusResponse);

        if (statusResponse.status === 'completed') {
          isPollingRef.current = false;
          setPhase('complete');
          const pid = processingId;
          setTimeout(() => onComplete(pid!), 1500);
        } else if (statusResponse.status === 'error') {
          isPollingRef.current = false;
          onError(statusResponse.error || 'Verarbeitung fehlgeschlagen');
        } else if (isTerminated(statusResponse)) {
          isPollingRef.current = false;
          const metadata = getTerminationMetadata(statusResponse);
          onError(metadata.message, metadata as unknown as Record<string, unknown>);
        }
      } catch (err) {
        console.error('Status polling error:', err as Error);
        isPollingRef.current = false;
        onError((err as Error).message);
      }
    };

    isPollingRef.current = true;
    pollStatus();
    const intervalId = setInterval(pollStatus, 2000);

    return () => {
      isPollingRef.current = false;
      clearInterval(intervalId);
    };
  }, [phase, processingId, onComplete, onError]);

  const handleCancel = async () => {
    try {
      if (processingIdRef.current) {
        await ApiService.cancelProcessing(processingIdRef.current);
      }
      isPollingRef.current = false;
      onCancel();
    } catch (err) {
      console.error('Cancel error:', err as Error);
    }
  };

  const formatElapsedTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds} Sek.`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins} Min. ${secs} Sek.`;
  };

  const getCurrentMessages = (): string[] => {
    const currentStatus = status?.status || 'extracting_text';
    return STEP_MESSAGES[currentStatus] || STEP_MESSAGES['extracting_text'];
  };

  const getRotatingMessage = (): string => {
    const messages = getCurrentMessages();
    return messages[rotatingMessageIndex % messages.length];
  };

  const getActiveStepIndex = (): number => {
    if (!status) return -1;
    if (status.status === 'completed') return STEPS.length;
    if (status.ui_stage) {
      const idx = STAGE_TO_CARD[status.ui_stage];
      if (idx !== undefined) return idx;
    }
    const stepText = (status.current_step || '').toLowerCase();
    if (stepText.includes('extrahiert') || stepText.includes('ocr')) return 0;
    if (
      stepText.includes('vereinfacht') ||
      stepText.includes('fakten') ||
      stepText.includes('grammatik')
    )
      return 3;
    if (stepText.includes('sprachübersetzung') || stepText.includes('qualitätsprüfung')) return 4;
    if (stepText.includes('formatierung') || stepText.includes('abgeschlossen')) return 5;
    if (stepText.includes('datenschutz') || stepText.includes('dokumenttyp')) return 2;
    if (stepText.includes('validiert')) return 1;
    const p = status.progress_percent;
    if (p < 10) return 0;
    if (p < 20) return 1;
    if (p < 40) return 2;
    if (p < 75) return 3;
    if (p < 95) return 4;
    return 5;
  };

  const getFileIcon = () => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return <FileText className="w-5 h-5 text-error-500" />;
    if (['jpg', 'jpeg', 'png'].includes(ext || ''))
      return <Image className="w-5 h-5 text-accent-500" />;
    return <FileText className="w-5 h-5 text-primary-500" />;
  };

  const getProgressColor = (): string => {
    if (phase === 'complete') return 'from-success-500 via-success-600 to-success-700';
    return 'from-brand-500 via-brand-600 to-accent-600';
  };

  // Upload + Initializing phase
  if (phase === 'uploading' || phase === 'initializing') {
    return (
      <Card className="animate-scale-in border-brand-200/50 shadow-medium">
        <CardContent className="p-6 sm:p-8">
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl sm:rounded-2xl flex items-center justify-center">
                  <Upload className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg sm:text-xl font-bold text-primary-900">
                    {phase === 'uploading'
                      ? 'Datei wird hochgeladen'
                      : 'Verarbeitung wird gestartet...'}
                  </h3>
                  <p className="text-xs sm:text-sm text-primary-600">
                    Bitte warten Sie einen Moment
                  </p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={handleCancel} title="Abbrechen">
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* File info */}
            <div className="flex items-center space-x-3 p-3 bg-neutral-50 rounded-lg border border-neutral-200">
              <div className="flex-shrink-0">{getFileIcon()}</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-primary-900 truncate">{file.name}</p>
                <p className="text-xs text-primary-500">{ApiService.formatFileSize(file.size)}</p>
              </div>
              <Badge variant="outline" className="text-xs">
                {phase === 'uploading' ? `${uploadProgress}%` : 'Bereit'}
              </Badge>
            </div>

            {/* Progress */}
            <div className="space-y-2">
              <Progress value={phase === 'initializing' ? 100 : uploadProgress} className="h-2" />
              <p className="text-center text-xs text-primary-500">
                {phase === 'uploading' && uploadProgress < 30 && 'Verbindung wird hergestellt...'}
                {phase === 'uploading' &&
                  uploadProgress >= 30 &&
                  uploadProgress < 60 &&
                  'Datei wird übertragen...'}
                {phase === 'uploading' &&
                  uploadProgress >= 60 &&
                  uploadProgress < 90 &&
                  'Fast fertig...'}
                {phase === 'uploading' && uploadProgress >= 90 && 'Qualitätsprüfung...'}
                {phase === 'initializing' && 'Verarbeitung wird vorbereitet...'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Complete phase
  if (phase === 'complete') {
    return (
      <Card className="animate-scale-in border-success-200/50 shadow-medium">
        <CardContent className="p-6 sm:p-8">
          <Alert className="border-success-200 bg-success-50/50">
            <Sparkles className="h-5 w-5 text-success-600" />
            <AlertDescription className="text-success-700 ml-2">
              <span className="font-semibold text-success-900">Übersetzung abgeschlossen!</span>
              <br />
              Ihr Dokument wurde erfolgreich in verständliche Sprache übersetzt. Das Ergebnis wird
              geladen...
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  // Processing phase
  return (
    <Card className="animate-scale-in shadow-medium">
      <CardContent className="p-6 sm:p-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 sm:mb-8 space-y-3 sm:space-y-0">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl sm:rounded-2xl flex items-center justify-center flex-shrink-0">
              {status?.status === 'completed' ? (
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

          <Button variant="ghost" size="icon" onClick={handleCancel} title="Verarbeitung abbrechen">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Status Display */}
        <div className="space-y-4 sm:space-y-6">
          {/* Current Status */}
          <div className="glass-effect p-4 sm:p-6 rounded-xl sm:rounded-2xl">
            <div className="flex items-center space-x-3 mb-4">
              {status ? (
                <>
                  {status.status === 'completed' ? (
                    <CheckCircle className="w-5 h-5 text-success-600" />
                  ) : status.status === 'error' ? (
                    <AlertCircle className="w-5 h-5 text-error-600" />
                  ) : (
                    <Loader className="w-5 h-5 text-brand-600 animate-spin" />
                  )}
                  <Badge
                    variant="outline"
                    className={
                      status.status === 'completed'
                        ? 'bg-success-50 text-success-700 border-success-200'
                        : status.status === 'error'
                          ? 'bg-error-50 text-error-700 border-error-200'
                          : 'bg-brand-50 text-brand-700 border-brand-200'
                    }
                  >
                    {ApiService.getStatusText(status.status)}
                  </Badge>
                  {status.status !== 'completed' && status.status !== 'error' && (
                    <div className="flex items-center text-xs text-brand-600">
                      <div className="w-2 h-2 bg-brand-500 rounded-full mr-2 animate-pulse"></div>
                      Aktiv
                    </div>
                  )}
                </>
              ) : (
                <>
                  <Loader className="w-5 h-5 text-brand-600 animate-spin" />
                  <Badge variant="outline" className="bg-brand-50 text-brand-700 border-brand-200">
                    Verbindung...
                  </Badge>
                </>
              )}
            </div>

            {/* Progress Bar */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-primary-700">Fortschritt</span>
                <div className="flex items-center space-x-2">
                  {(!status || (status.status !== 'completed' && status.status !== 'error')) && (
                    <div className="w-1.5 h-1.5 bg-brand-500 rounded-full animate-pulse"></div>
                  )}
                  <span className="font-bold text-primary-900">
                    {Math.round(displayedProgress)}%
                  </span>
                </div>
              </div>

              <div className="progress-bar h-3">
                <div
                  className={`progress-fill bg-gradient-to-r ${getProgressColor()} transition-none`}
                  style={{ width: `${displayedProgress}%` }}
                />
              </div>

              {status?.current_step && (
                <p className="text-sm text-primary-600 leading-relaxed">{status.current_step}</p>
              )}

              {status && status.status !== 'completed' && status.status !== 'error' && (
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
                const activeIdx = getActiveStepIndex();
                const completed = index < activeIdx;
                const active = index === activeIdx;
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

          {/* Status messages */}
          {status?.message && (
            <div className="glass-effect p-4 rounded-xl border border-brand-200/50">
              <div className="text-brand-700 text-sm leading-relaxed">{status.message}</div>
            </div>
          )}

          {/* Processing ID */}
          {processingId && (
            <div className="text-center">
              <p className="text-xs text-primary-500">
                Verarbeitungs-ID: <span className="font-mono">{processingId}</span>
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default DocumentProcessor;
