import React, { useState, useEffect } from 'react';
import { Stethoscope, Shield, Clock, AlertTriangle } from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import TranslationResult from './components/TranslationResult';
import ApiService from './services/api';
import { UploadResponse, TranslationResult as TranslationData, HealthCheck } from './types/api';

type AppState = 'upload' | 'processing' | 'result' | 'error';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [translationResult, setTranslationResult] = useState<TranslationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthCheck | null>(null);

  // Health check beim Start
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthResponse = await ApiService.getHealth();
        setHealth(healthResponse);
      } catch (error) {
        console.error('Health check failed:', error);
      }
    };

    checkHealth();
  }, []);

  const handleUploadSuccess = async (response: UploadResponse) => {
    setUploadResponse(response);
    setError(null);
    
    try {
      // Verarbeitung automatisch starten
      await ApiService.startProcessing(response.processing_id);
      setAppState('processing');
    } catch (error: any) {
      setError(error.message);
      setAppState('error');
    }
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
    setAppState('error');
  };

  const handleProcessingComplete = async () => {
    if (!uploadResponse) return;

    try {
      const result = await ApiService.getProcessingResult(uploadResponse.processing_id);
      setTranslationResult(result);
      setAppState('result');
    } catch (error: any) {
      setError(error.message);
      setAppState('error');
    }
  };

  const handleProcessingError = (errorMessage: string) => {
    setError(errorMessage);
    setAppState('error');
  };

  const handleProcessingCancel = () => {
    setAppState('upload');
    setUploadResponse(null);
    setError(null);
  };

  const handleNewTranslation = () => {
    setAppState('upload');
    setUploadResponse(null);
    setTranslationResult(null);
    setError(null);
  };

  const renderHealthIndicator = () => {
    if (!health) return null;

    const isHealthy = health.status === 'healthy';
    const hasWarnings = health.status === 'degraded';

    return (
      <div className={`flex items-center space-x-2 text-sm ${
        isHealthy ? 'text-success-600' : hasWarnings ? 'text-warning-600' : 'text-error-600'
      }`}>
        {isHealthy ? (
          <Shield className="w-4 h-4" />
        ) : (
          <AlertTriangle className="w-4 h-4" />
        )}
        <span>
          System: {isHealthy ? 'Einsatzbereit' : hasWarnings ? 'Eingeschränkt' : 'Fehler'}
        </span>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="medical-gradient p-2 rounded-lg">
                <Stethoscope className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  Medizinische Dokumenten-Übersetzung
                </h1>
                <p className="text-sm text-gray-600">
                  DSGVO-konforme Übersetzung in einfache Sprache
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {renderHealthIndicator()}
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <Clock className="w-4 h-4" />
                <span>{new Date().toLocaleTimeString('de-DE')}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error State */}
        {appState === 'error' && (
          <div className="space-y-6">
            <div className="card border-error-200 bg-error-50">
              <div className="card-body">
                <div className="flex items-center space-x-3">
                  <AlertTriangle className="w-6 h-6 text-error-600" />
                  <div>
                    <h3 className="text-lg font-semibold text-error-800">
                      Fehler bei der Verarbeitung
                    </h3>
                    <p className="text-error-700 mt-1">
                      {error}
                    </p>
                  </div>
                </div>
                
                <div className="mt-4">
                  <button
                    onClick={handleNewTranslation}
                    className="btn-primary"
                  >
                    Neuen Versuch starten
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Upload State */}
        {appState === 'upload' && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                Medizinische Dokumente verstehen
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                Laden Sie Arztbriefe, Befunde oder andere medizinische Dokumente hoch 
                und erhalten Sie eine verständliche Übersetzung in einfacher Sprache.
              </p>
            </div>
            
            <FileUpload
              onUploadSuccess={handleUploadSuccess}
              onUploadError={handleUploadError}
            />

            {/* Features */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
              <div className="text-center p-6 bg-white rounded-xl shadow-sm">
                <div className="w-12 h-12 medical-gradient rounded-lg mx-auto mb-4 flex items-center justify-center">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">DSGVO-konform</h3>
                <p className="text-sm text-gray-600">
                  Keine Speicherung Ihrer Daten. Alle Informationen werden nach der Übersetzung gelöscht.
                </p>
              </div>
              
              <div className="text-center p-6 bg-white rounded-xl shadow-sm">
                <div className="w-12 h-12 medical-gradient rounded-lg mx-auto mb-4 flex items-center justify-center">
                  <Stethoscope className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Medizinisch optimiert</h3>
                <p className="text-sm text-gray-600">
                  Speziell für medizinische Fachbegriffe und Dokumente entwickelt.
                </p>
              </div>
              
              <div className="text-center p-6 bg-white rounded-xl shadow-sm">
                <div className="w-12 h-12 medical-gradient rounded-lg mx-auto mb-4 flex items-center justify-center">
                  <Clock className="w-6 h-6 text-white" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Schnell & einfach</h3>
                <p className="text-sm text-gray-600">
                  Erhalten Sie in wenigen Minuten eine verständliche Übersetzung.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Processing State */}
        {appState === 'processing' && uploadResponse && (
          <ProcessingStatus
            processingId={uploadResponse.processing_id}
            onComplete={handleProcessingComplete}
            onError={handleProcessingError}
            onCancel={handleProcessingCancel}
          />
        )}

        {/* Result State */}
        {appState === 'result' && translationResult && (
          <TranslationResult
            result={translationResult}
            onNewTranslation={handleNewTranslation}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="mt-16 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <div className="medical-gradient p-1 rounded">
                <Stethoscope className="w-4 h-4 text-white" />
              </div>
              <span className="text-sm font-medium text-gray-900">
                Medizinische Dokumenten-Übersetzung
              </span>
            </div>
            
            <div className="text-xs text-gray-500 space-y-1">
              <div>
                Diese Anwendung dient nur der Orientierung und ersetzt nicht die professionelle medizinische Beratung.
              </div>
              <div>
                Alle Daten werden DSGVO-konform verarbeitet und nicht gespeichert.
              </div>
              <div className="pt-2">
                Version 1.0.0 | Powered by Ollama & FastAPI
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App; 