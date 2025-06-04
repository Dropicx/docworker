import React, { useState, useEffect } from 'react';
import { Stethoscope, Shield, Clock, AlertTriangle, Sparkles, FileText, Zap } from 'lucide-react';
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
      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium ${
        isHealthy ? 'bg-success-50 text-success-700 ring-1 ring-success-200' : 
        hasWarnings ? 'bg-warning-50 text-warning-700 ring-1 ring-warning-200' : 
        'bg-error-50 text-error-700 ring-1 ring-error-200'
      }`}>
        {isHealthy ? (
          <Shield className="w-3 h-3" />
        ) : (
          <AlertTriangle className="w-3 h-3" />
        )}
        <span>
          {isHealthy ? 'System bereit' : hasWarnings ? 'Eingeschränkt' : 'Systemfehler'}
        </span>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30">
      {/* Header */}
      <header className="sticky top-0 z-50 header-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center space-x-4">
              <div className="hero-gradient p-3 rounded-2xl shadow-soft">
                <Stethoscope className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-primary-900 tracking-tight">
                  DocTranslator
                </h1>
                <p className="text-sm text-primary-600 font-medium">
                  Medizinische Dokumente verstehen
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-6">
              {renderHealthIndicator()}
              <div className="flex items-center space-x-2 text-xs text-primary-500 bg-primary-50 px-3 py-1.5 rounded-full">
                <Clock className="w-3 h-3" />
                <span>{new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-0 left-0 w-72 h-72 bg-gradient-to-r from-brand-400/20 to-accent-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse-soft"></div>
          <div className="absolute bottom-0 right-0 w-72 h-72 bg-gradient-to-r from-accent-400/20 to-brand-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse-soft" style={{ animationDelay: '1s' }}></div>
        </div>

        <div className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Error State */}
          {appState === 'error' && (
            <div className="animate-fade-in">
              <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white">
                <div className="card-body">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
                      <AlertTriangle className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-error-900 mb-2">
                        Verarbeitung fehlgeschlagen
                      </h3>
                      <p className="text-error-700 mb-6 leading-relaxed">
                        {error}
                      </p>
                      <button
                        onClick={handleNewTranslation}
                        className="btn-primary"
                      >
                        <Sparkles className="w-4 h-4 mr-2" />
                        Neuen Versuch starten
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Upload State */}
          {appState === 'upload' && (
            <div className="space-y-16 animate-fade-in">
              {/* Hero Section */}
              <div className="text-center space-y-8">
                <div className="space-y-4">
                  <h2 className="text-hero bg-gradient-to-r from-primary-900 via-brand-700 to-accent-700 bg-clip-text text-transparent">
                    Medizinische Dokumente
                    <br />
                    <span className="bg-gradient-to-r from-brand-600 to-accent-600 bg-clip-text text-transparent">
                      einfach verstehen
                    </span>
                  </h2>
                  <p className="text-lead max-w-3xl mx-auto">
                    Verwandeln Sie komplexe Arztbriefe und medizinische Befunde in verständliche Sprache. 
                    Schnell, sicher und DSGVO-konform.
                  </p>
                </div>
                
                {/* Quick Stats */}
                <div className="flex justify-center space-x-8 text-sm">
                  <div className="flex items-center space-x-2 text-primary-600">
                    <div className="w-2 h-2 bg-brand-500 rounded-full"></div>
                    <span className="font-medium">100% DSGVO-konform</span>
                  </div>
                  <div className="flex items-center space-x-2 text-primary-600">
                    <div className="w-2 h-2 bg-accent-500 rounded-full"></div>
                    <span className="font-medium">Sofortige Verarbeitung</span>
                  </div>
                  <div className="flex items-center space-x-2 text-primary-600">
                    <div className="w-2 h-2 bg-brand-500 rounded-full"></div>
                    <span className="font-medium">Keine Speicherung</span>
                  </div>
                </div>
              </div>
              
              {/* Upload Component */}
              <div className="animate-slide-up">
                <FileUpload
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={handleUploadError}
                />
              </div>

              {/* Features */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="feature-card animate-slide-up" style={{ animationDelay: '0.1s' }}>
                  <div className="feature-icon">
                    <Shield className="w-7 h-7" />
                  </div>
                  <h3 className="text-xl font-bold text-primary-900 mb-3">
                    Datenschutz first
                  </h3>
                  <p className="text-primary-600 leading-relaxed">
                    Keine Speicherung Ihrer Daten. Alle Informationen werden nach der 
                    Übersetzung automatisch gelöscht.
                  </p>
                </div>
                
                <div className="feature-card animate-slide-up" style={{ animationDelay: '0.2s' }}>
                  <div className="feature-icon">
                    <FileText className="w-7 h-7" />
                  </div>
                  <h3 className="text-xl font-bold text-primary-900 mb-3">
                    Medizinisch präzise
                  </h3>
                  <p className="text-primary-600 leading-relaxed">
                    Speziell für medizinische Fachbegriffe und Dokumente entwickelt. 
                    Präzise Übersetzungen ohne Informationsverlust.
                  </p>
                </div>
                
                <div className="feature-card animate-slide-up" style={{ animationDelay: '0.3s' }}>
                  <div className="feature-icon">
                    <Zap className="w-7 h-7" />
                  </div>
                  <h3 className="text-xl font-bold text-primary-900 mb-3">
                    Blitzschnell
                  </h3>
                  <p className="text-primary-600 leading-relaxed">
                    Erhalten Sie in wenigen Sekunden eine verständliche Übersetzung 
                    Ihrer medizinischen Dokumente.
                  </p>
                </div>
              </div>

              {/* Trust Indicators */}
              <div className="glass-card p-8 text-center">
                <p className="text-sm text-primary-600 mb-4 font-medium">
                  Vertraut von Patienten und medizinischen Einrichtungen
                </p>
                <div className="flex justify-center items-center space-x-8 opacity-60">
                  <div className="h-8 w-24 bg-gradient-to-r from-primary-200 to-primary-300 rounded-lg"></div>
                  <div className="h-8 w-20 bg-gradient-to-r from-brand-200 to-brand-300 rounded-lg"></div>
                  <div className="h-8 w-28 bg-gradient-to-r from-accent-200 to-accent-300 rounded-lg"></div>
                  <div className="h-8 w-22 bg-gradient-to-r from-primary-200 to-primary-300 rounded-lg"></div>
                </div>
              </div>
            </div>
          )}

          {/* Processing State */}
          {appState === 'processing' && uploadResponse && (
            <div className="animate-fade-in">
              <ProcessingStatus
                processingId={uploadResponse.processing_id}
                onComplete={handleProcessingComplete}
                onError={handleProcessingError}
                onCancel={handleProcessingCancel}
              />
            </div>
          )}

          {/* Result State */}
          {appState === 'result' && translationResult && (
            <div className="animate-fade-in">
              <TranslationResult
                result={translationResult}
                onNewTranslation={handleNewTranslation}
              />
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 mt-24 border-t border-primary-100/50 bg-gradient-to-r from-white/80 to-neutral-50/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center space-y-6">
            <div className="flex items-center justify-center space-x-3">
              <div className="hero-gradient p-2 rounded-lg">
                <Stethoscope className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold text-primary-900">
                DocTranslator
              </span>
            </div>
            
            <div className="flex justify-center space-x-8 text-sm text-primary-600">
              <span>© 2024 DocTranslator</span>
              <span>•</span>
              <span>DSGVO-konform</span>
              <span>•</span>
              <span>Made with ❤️ for better healthcare</span>
            </div>
            
            <p className="text-xs text-primary-500 max-w-2xl mx-auto">
              Dieses Tool dient der Unterstützung beim Verständnis medizinischer Dokumente 
              und ersetzt nicht die professionelle medizinische Beratung.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App; 