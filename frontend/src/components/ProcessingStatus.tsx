import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, AlertCircle, Loader, RefreshCw, X, Sparkles, Zap, FileCheck } from 'lucide-react';
import ApiService from '../services/api';
import { ProcessingProgress, ProcessingStatus as Status } from '../types/api';

interface ProcessingStatusProps {
  processingId: string;
  onComplete: () => void;
  onError: (error: string) => void;
  onCancel?: () => void;
}

const ProcessingStatus: React.FC<ProcessingStatusProps> = ({
  processingId,
  onComplete,
  onError,
  onCancel
}) => {
  const [status, setStatus] = useState<ProcessingProgress | null>(null);
  const [isPolling, setIsPolling] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const statusResponse = await ApiService.getProcessingStatus(processingId);
        setStatus(statusResponse);
        
        if (statusResponse.status === 'completed') {
          setIsPolling(false);
          setTimeout(onComplete, 1500); // Etwas längere Verzögerung für bessere UX
        } else if (statusResponse.status === 'error') {
          setIsPolling(false);
          setError(statusResponse.error || 'Unbekannter Fehler');
          onError(statusResponse.error || 'Verarbeitung fehlgeschlagen');
        }
      } catch (err: any) {
        console.error('Status polling error:', err);
        setError(err.message);
        setIsPolling(false);
        onError(err.message);
      }
    };

    if (isPolling) {
      pollStatus(); // Sofort ausführen
      intervalId = setInterval(pollStatus, 2000); // Alle 2 Sekunden
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
    } catch (err: any) {
      console.error('Cancel error:', err);
      setError(err.message);
    }
  };

  const getStatusIcon = (status: Status) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-5 h-5 text-warning-600" />;
      case 'processing':
      case 'extracting_text':
      case 'translating':
        return <Loader className="w-5 h-5 text-brand-600 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-success-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-600" />;
      default:
        return <RefreshCw className="w-5 h-5 text-primary-600" />;
    }
  };

  const getProgressColor = (status: Status) => {
    switch (status) {
      case 'completed':
        return 'from-success-500 via-success-600 to-success-700';
      case 'error':
        return 'from-error-500 via-error-600 to-error-700';
      default:
        return 'from-brand-500 via-brand-600 to-accent-600';
    }
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
        {/* Header - Mobile Optimized */}
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
              <h3 className="text-lg sm:text-xl font-bold text-primary-900">
                KI-Verarbeitung
              </h3>
              <p className="text-xs sm:text-sm text-primary-600">
                Ihr Dokument wird analysiert und übersetzt
              </p>
              <p className="text-xs text-primary-500 mt-1">
                Dies kann bis zu 3 Minuten dauern
              </p>
            </div>
          </div>
          
          {(status.status === 'pending' || status.status === 'processing' || 
            status.status === 'extracting_text' || status.status === 'translating') && onCancel && (
            <button
              onClick={handleCancel}
              className="p-2 text-primary-400 hover:text-primary-600 hover:bg-primary-50 rounded-xl transition-all duration-200"
              title="Verarbeitung abbrechen"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Status Display - Mobile Optimized */}
        <div className="space-y-4 sm:space-y-6">
          {/* Current Status */}
          <div className="glass-effect p-4 sm:p-6 rounded-xl sm:rounded-2xl">
            <div className="flex items-center space-x-3 mb-4">
              {getStatusIcon(status.status)}
              <span className={`status-badge ${ApiService.getStatusColor(status.status)}`}>
                {ApiService.getStatusText(status.status)}
              </span>
              {status.status === 'completed' && (
                <div className="flex items-center text-xs text-success-600">
                  <div className="w-2 h-2 bg-success-500 rounded-full mr-2 animate-pulse-soft"></div>
                  Abgeschlossen
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-primary-700">Fortschritt</span>
                <span className="font-bold text-primary-900">{status.progress_percent}%</span>
              </div>
              
              <div className="progress-bar h-3">
                <div
                  className={`progress-fill bg-gradient-to-r ${getProgressColor(status.status)} transition-all duration-700 ease-out`}
                  style={{ width: `${status.progress_percent}%` }}
                />
              </div>

              <p className="text-sm text-primary-600 leading-relaxed">
                {status.current_step}
              </p>
            </div>
          </div>

          {/* Processing Steps - Mobile Optimized */}
          <div className="space-y-3 sm:space-y-4">
            <h4 className="text-base sm:text-lg font-semibold text-primary-900 flex items-center">
              <FileCheck className="w-4 h-4 sm:w-5 sm:h-5 mr-2 text-brand-600" />
              Verarbeitungsschritte
            </h4>
            
            <div className="space-y-2 sm:space-y-3">
              {[
                { 
                  step: 'upload', 
                  label: 'Dokument hochgeladen', 
                  icon: CheckCircle,
                  completed: status.progress_percent >= 10,
                  active: status.progress_percent >= 0 && status.progress_percent < 30
                },
                { 
                  step: 'extract', 
                  label: 'Text wird extrahiert', 
                  icon: Loader,
                  completed: status.progress_percent >= 30,
                  active: status.progress_percent >= 10 && status.progress_percent < 70
                },
                { 
                  step: 'translate', 
                  label: 'KI übersetzt das Dokument', 
                  icon: Zap,
                  completed: status.progress_percent >= 70,
                  active: status.progress_percent >= 30 && status.progress_percent < 100
                },
                { 
                  step: 'finalize', 
                  label: 'Übersetzung wird finalisiert', 
                  icon: Sparkles,
                  completed: status.progress_percent >= 100,
                  active: status.progress_percent >= 70 && status.progress_percent < 100
                }
              ].map((item, index) => {
                const IconComponent = item.icon;
                return (
                  <div key={index} className={`flex items-center space-x-3 sm:space-x-4 p-3 sm:p-4 rounded-lg sm:rounded-xl transition-all duration-300 ${
                    item.completed 
                      ? 'bg-gradient-to-r from-success-50 to-success-50/50 border border-success-200' 
                      : item.active 
                        ? 'bg-gradient-to-r from-brand-50 to-accent-50/50 border border-brand-200' 
                        : 'bg-neutral-50 border border-neutral-200'
                  }`}>
                    <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-lg sm:rounded-xl flex items-center justify-center transition-all duration-300 flex-shrink-0 ${
                      item.completed 
                        ? 'bg-gradient-to-br from-success-500 to-success-600' 
                        : item.active 
                          ? 'bg-gradient-to-br from-brand-500 to-brand-600' 
                          : 'bg-neutral-200'
                    }`}>
                      <IconComponent className={`w-4 h-4 sm:w-5 sm:h-5 ${
                        item.completed || item.active ? 'text-white' : 'text-neutral-500'
                      } ${item.active && !item.completed ? 'animate-pulse-soft' : ''}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm sm:text-base font-medium truncate ${
                        item.completed 
                          ? 'text-success-900' 
                          : item.active 
                            ? 'text-brand-900' 
                            : 'text-neutral-600'
                      }`}>
                        {item.label}
                      </div>
                    </div>
                    {item.completed && (
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
                    <h4 className="font-semibold text-error-900 mb-1">Verarbeitung fehlgeschlagen</h4>
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
                    <h4 className="font-semibold text-success-900 mb-1">Übersetzung abgeschlossen!</h4>
                    <p className="text-success-700 text-sm leading-relaxed">
                      Ihr Dokument wurde erfolgreich in verständliche Sprache übersetzt. Das Ergebnis wird geladen...
                    </p>
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