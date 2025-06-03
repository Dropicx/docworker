import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, AlertCircle, Loader, RefreshCw, X } from 'lucide-react';
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
          setTimeout(onComplete, 1000); // Kurze Verzögerung für UX
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
        return <Loader className="w-5 h-5 text-medical-600 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-success-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-error-600" />;
      default:
        return <RefreshCw className="w-5 h-5 text-gray-600" />;
    }
  };

  const getProgressColor = (status: Status) => {
    switch (status) {
      case 'completed':
        return 'from-success-500 to-success-600';
      case 'error':
        return 'from-error-500 to-error-600';
      default:
        return 'from-medical-500 to-medical-600';
    }
  };

  if (!status) {
    return (
      <div className="card animate-slide-up">
        <div className="card-body">
          <div className="flex items-center justify-center py-8">
            <Loader className="w-8 h-8 text-medical-600 animate-spin mr-3" />
            <span className="text-gray-600">Status wird geladen...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card animate-slide-up">
      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Verarbeitungsfortschritt
          </h3>
          
          {(status.status === 'pending' || status.status === 'processing' || 
            status.status === 'extracting_text' || status.status === 'translating') && onCancel && (
            <button
              onClick={handleCancel}
              className="p-2 text-gray-500 hover:text-gray-700 rounded-lg hover:bg-gray-100"
              title="Verarbeitung abbrechen"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Status Badge */}
        <div className="flex items-center mb-4">
          {getStatusIcon(status.status)}
          <span className={`ml-2 status-badge ${ApiService.getStatusColor(status.status)}`}>
            {ApiService.getStatusText(status.status)}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Fortschritt</span>
            <span>{status.progress_percent}%</span>
          </div>
          
          <div className="progress-bar">
            <div
              className={`progress-fill bg-gradient-to-r ${getProgressColor(status.status)}`}
              style={{ width: `${status.progress_percent}%` }}
            />
          </div>
        </div>

        {/* Current Step */}
        <div className="text-sm text-gray-600 mb-4">
          <strong>Aktueller Schritt:</strong> {status.current_step}
        </div>

        {/* Processing ID */}
        <div className="text-xs text-gray-500 mb-4">
          <strong>Verarbeitungs-ID:</strong> {status.processing_id}
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center p-3 bg-error-50 border border-error-200 rounded-lg">
            <AlertCircle className="w-5 h-5 text-error-600 mr-2 flex-shrink-0" />
            <div className="text-error-700 text-sm">{error}</div>
          </div>
        )}

        {/* Status Message */}
        {status.message && !error && (
          <div className="p-3 bg-medical-50 border border-medical-200 rounded-lg">
            <div className="text-medical-700 text-sm">{status.message}</div>
          </div>
        )}

        {/* Completion Message */}
        {status.status === 'completed' && (
          <div className="flex items-center p-3 bg-success-50 border border-success-200 rounded-lg">
            <CheckCircle className="w-5 h-5 text-success-600 mr-2" />
            <div className="text-success-700 text-sm">
              Verarbeitung erfolgreich abgeschlossen! Das Ergebnis wird geladen...
            </div>
          </div>
        )}

        {/* Processing Steps */}
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Verarbeitungsschritte</h4>
          <div className="space-y-2">
            {[
              { step: 'pending', label: 'Upload abgeschlossen', completed: status.progress_percent >= 10 },
              { step: 'extracting_text', label: 'Text-Extraktion', completed: status.progress_percent >= 30 },
              { step: 'translating', label: 'KI-Übersetzung', completed: status.progress_percent >= 70 },
              { step: 'completed', label: 'Fertigstellung', completed: status.progress_percent >= 100 }
            ].map((item, index) => (
              <div key={index} className="flex items-center">
                <div
                  className={`w-3 h-3 rounded-full mr-3 ${
                    item.completed
                      ? 'bg-success-500'
                      : status.current_step.toLowerCase().includes(item.step)
                      ? 'bg-medical-500 animate-pulse'
                      : 'bg-gray-300'
                  }`}
                />
                <span
                  className={`text-sm ${
                    item.completed
                      ? 'text-success-700 font-medium'
                      : status.current_step.toLowerCase().includes(item.step)
                      ? 'text-medical-700 font-medium'
                      : 'text-gray-600'
                  }`}
                >
                  {item.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Timestamp */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            Letzte Aktualisierung: {new Date(status.timestamp).toLocaleTimeString('de-DE')}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProcessingStatus; 