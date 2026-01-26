import { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import {
  Shield,
  AlertTriangle,
  Sparkles,
  FileText,
  Zap,
  Stethoscope,
} from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import Header from './components/Header';
import { ChatPage } from './components/chat';
import TranslationResult from './components/TranslationResult';
import TerminationCard from './components/TerminationCard';
import Footer from './components/Footer';
import FAQ from './components/FAQ';
import CookieFreeBanner from './components/CookieFreeBanner';
import Impressum from './pages/Impressum';
import Datenschutz from './pages/Datenschutz';
import Nutzungsbedingungen from './pages/Nutzungsbedingungen';
import Login from './pages/Login';
import SettingsPage from './pages/Settings';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ApiService from './services/api';
import {
  UploadResponse,
  TranslationResult as TranslationData,
  HealthCheck,
  ProcessingOptions,
  SupportedLanguage,
} from './types/api';

type AppState = 'upload' | 'initializing' | 'processing' | 'result' | 'error';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [translationResult, setTranslationResult] = useState<TranslationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorMetadata, setErrorMetadata] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [availableLanguages, setAvailableLanguages] = useState<SupportedLanguage[]>([]);
  const [languagesLoaded, setLanguagesLoaded] = useState(false);

  // Health check beim Start
  useEffect(() => {
    let mounted = true;
    let healthCheckDone = false;
    let languagesCheckDone = false;

    const checkHealth = async () => {
      if (healthCheckDone) return;
      healthCheckDone = true;

      try {
        const healthResponse = await ApiService.getHealth();
        if (mounted) {
          setHealth(healthResponse);
        }
      } catch (error) {
        console.error('Health check failed:', error);
      }
    };

    const loadLanguages = async () => {
      if (languagesCheckDone) return;
      languagesCheckDone = true;

      try {
        const languagesResponse = await ApiService.getAvailableLanguages();
        if (mounted) {
          setAvailableLanguages(languagesResponse.languages);
          setLanguagesLoaded(true);
        }
      } catch (error) {
        console.error('Language loading failed:', error);
        if (mounted) {
          setLanguagesLoaded(true); // Set true even on error to show UI
        }
      }
    };

    checkHealth();
    loadLanguages();

    return () => {
      mounted = false;
    };
  }, []);

  const handleUploadSuccess = async (response: UploadResponse, selectedLanguage: string | null) => {
    setUploadResponse(response);
    setError(null);
    // Show initializing screen immediately
    setAppState('initializing');

    try {
      // Small delay to show the initializing screen
      await new Promise(resolve => setTimeout(resolve, 500));

      // Start processing with language options
      const options: ProcessingOptions = {};
      if (selectedLanguage) {
        options.target_language = selectedLanguage;
      }

      await ApiService.startProcessing(response.processing_id, options);
      setAppState('processing');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Ein unbekannter Fehler ist aufgetreten');
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

      // Check if processing was terminated (e.g., non-medical content)
      if (result.terminated) {
        const metadata = {
          isTermination: true,
          reason: result.termination_reason,
          step: result.termination_step,
        };
        handleProcessingError(
          result.termination_message || 'Verarbeitung wurde gestoppt',
          metadata
        );
        return;
      }

      // Normal completion
      setTranslationResult(result);
      setAppState('result');
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Ein unbekannter Fehler ist aufgetreten');
      setAppState('error');
    }
  };

  const handleProcessingError = (errorMessage: string, metadata?: Record<string, unknown>) => {
    setError(errorMessage);
    setErrorMetadata(metadata || null);
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
    setErrorMetadata(null);
  };

  const MainApp = () => {
    return (
      <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
        <Header health={health} onLogoClick={handleNewTranslation} />

        {/* Main Content */}
        <main className="relative">
          {/* Background Pattern */}
          <div className="absolute inset-0 opacity-30">
            <div className="absolute top-0 left-0 w-72 h-72 bg-gradient-to-r from-brand-400/20 to-accent-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse-soft"></div>
            <div
              className="absolute bottom-0 right-0 w-72 h-72 bg-gradient-to-r from-accent-400/20 to-brand-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse-soft"
              style={{ animationDelay: '1s' }}
            ></div>
          </div>

          <div className="relative z-10 max-w-5xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
            {/* Error State */}
            {appState === 'error' && (
              <div className="animate-fade-in">
                {errorMetadata?.isTermination ? (
                  <TerminationCard
                    message={error || 'Verarbeitung wurde gestoppt'}
                    reason={errorMetadata.reason as string | undefined}
                    step={errorMetadata.step as string | undefined}
                    onReset={handleNewTranslation}
                  />
                ) : (
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
                          <p className="text-error-700 mb-6 leading-relaxed">{error}</p>
                          <button onClick={handleNewTranslation} className="btn-primary">
                            <Sparkles className="w-4 h-4 mr-2" />
                            Neuen Versuch starten
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Upload State - Mobile Optimized */}
            {appState === 'upload' && (
              <div className="space-y-8 sm:space-y-12 lg:space-y-16">
                {/* Hero Section - Mobile Optimized */}
                <div className="text-center space-y-4 sm:space-y-6 lg:space-y-8">
                  <div className="space-y-3 sm:space-y-4">
                    <h2 className="text-hero bg-gradient-to-r from-primary-900 via-brand-700 to-accent-700 bg-clip-text text-transparent px-2">
                      Medizinische Dokumente
                      <br className="hidden sm:block" />
                      <span className="sm:hidden"> </span>
                      <span className="bg-gradient-to-r from-brand-600 to-accent-600 bg-clip-text text-transparent">
                        einfach verstehen
                      </span>
                    </h2>
                    <p className="text-lead max-w-3xl mx-auto px-4 sm:px-0">
                      Verwandeln Sie komplexe Arztbriefe und medizinische Befunde in verständliche
                      Sprache.
                      <span className="hidden sm:inline"> Schnell, sicher und DSGVO-konform.</span>
                      <span className="sm:hidden block mt-2">
                        Schnell, sicher und DSGVO-konform.
                      </span>
                    </p>
                  </div>

                  {/* Quick Stats - Mobile Optimized */}
                  <div className="flex flex-col sm:flex-row justify-center items-center space-y-2 sm:space-y-0 sm:space-x-6 lg:space-x-8 text-xs sm:text-sm">
                    <div className="flex items-center space-x-2 text-primary-600">
                      <div className="w-2 h-2 bg-brand-500 rounded-full"></div>
                      <span className="font-medium">100% DSGVO</span>
                    </div>
                    <div className="flex items-center space-x-2 text-primary-600">
                      <div className="w-2 h-2 bg-accent-500 rounded-full"></div>
                      <span className="font-medium">Sofort bereit</span>
                    </div>
                    <div className="flex items-center space-x-2 text-primary-600">
                      <div className="w-2 h-2 bg-brand-500 rounded-full"></div>
                      <span className="font-medium">Keine Speicherung</span>
                    </div>
                  </div>
                </div>

                {/* Upload Component with Language Selector */}
                <div>
                  <FileUpload
                    onUploadSuccess={handleUploadSuccess}
                    onUploadError={handleUploadError}
                    availableLanguages={availableLanguages}
                    languagesLoaded={languagesLoaded}
                  />
                </div>

                {/* Features - Mobile Optimized */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
                  <div className="feature-card">
                    <div className="feature-icon">
                      <Shield className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                      Datenschutz first
                    </h3>
                    <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                      Keine Speicherung Ihrer Daten. Alle Informationen werden nach der Übersetzung
                      automatisch gelöscht.
                    </p>
                  </div>

                  <div className="feature-card">
                    <div className="feature-icon">
                      <FileText className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                      Medizinisch präzise
                    </h3>
                    <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                      Speziell für medizinische Fachbegriffe und Dokumente entwickelt. Präzise
                      Übersetzungen ohne Informationsverlust.
                    </p>
                  </div>

                  <div className="feature-card sm:col-span-2 lg:col-span-1">
                    <div className="feature-icon">
                      <Zap className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                      Blitzschnell
                    </h3>
                    <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                      Erhalten Sie in wenigen Sekunden eine verständliche Übersetzung Ihrer
                      medizinischen Dokumente.
                    </p>
                  </div>
                </div>

                {/* FAQ Section */}
                <div className="mt-12 sm:mt-16 lg:mt-20">
                  <FAQ />
                </div>
              </div>
            )}

            {/* Initializing State - Temporary screen */}
            {appState === 'initializing' && (
              <div className="animate-fade-in">
                <div className="card-elevated">
                  <div className="card-body">
                    <div className="flex flex-col items-center justify-center space-y-6 py-8">
                      {/* Animated icon */}
                      <div className="relative">
                        <div className="w-20 h-20 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl flex items-center justify-center animate-pulse">
                          <Stethoscope className="w-10 h-10 text-white" />
                        </div>
                        <div className="absolute inset-0 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl opacity-30 animate-ping" />
                      </div>

                      {/* German text */}
                      <div className="text-center space-y-2">
                        <h3 className="text-2xl font-bold text-primary-900">
                          Analyse wird gestartet
                        </h3>
                        <p className="text-primary-600">Ihr Dokument wird vorbereitet...</p>
                      </div>

                      {/* Loading dots */}
                      <div className="flex space-x-2">
                        <div
                          className="w-2 h-2 bg-brand-500 rounded-full animate-bounce"
                          style={{ animationDelay: '0ms' }}
                        />
                        <div
                          className="w-2 h-2 bg-brand-500 rounded-full animate-bounce"
                          style={{ animationDelay: '150ms' }}
                        />
                        <div
                          className="w-2 h-2 bg-brand-500 rounded-full animate-bounce"
                          style={{ animationDelay: '300ms' }}
                        />
                      </div>
                    </div>
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

        <Footer />
        <CookieFreeBanner />
      </div>
    );
  };

  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<MainApp />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
        <Route path="/impressum" element={<Impressum />} />
        <Route path="/datenschutz" element={<Datenschutz />} />
        <Route path="/nutzungsbedingungen" element={<Nutzungsbedingungen />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
