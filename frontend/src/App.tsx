import { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Shield, AlertTriangle, Sparkles, FileText, Zap } from 'lucide-react';
import { Card, CardHeader, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import FileUpload from './components/FileUpload';
import DocumentProcessor from './components/DocumentProcessor';
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
import { AuthProvider } from './contexts/AuthContext';
import ApiService from './services/api';
import {
  TranslationResult as TranslationData,
  HealthCheck,
  QualityGateErrorDetails,
  SupportedLanguage,
} from './types/api';

type AppState = 'upload' | 'processing' | 'result' | 'error';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [translationResult, setTranslationResult] = useState<TranslationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorMetadata, setErrorMetadata] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [availableLanguages, setAvailableLanguages] = useState<SupportedLanguage[]>([]);
  const [languagesLoaded, setLanguagesLoaded] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingLanguage, setPendingLanguage] = useState<string | null>(null);
  const [qualityGateError, setQualityGateError] = useState<QualityGateErrorDetails | null>(null);

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

  const handleStartProcessing = (file: File, language: string | null) => {
    setPendingFile(file);
    setPendingLanguage(language);
    setQualityGateError(null);
    setError(null);
    setAppState('processing');
  };

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage);
    setAppState('error');
  };

  const handleProcessingComplete = async (processingId?: string) => {
    if (!processingId) return;
    const pid = processingId;

    try {
      const result = await ApiService.getProcessingResult(pid);

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
    setPendingFile(null);
    setPendingLanguage(null);
    setError(null);
  };

  const handleNewTranslation = () => {
    setAppState('upload');
    setPendingFile(null);
    setPendingLanguage(null);
    setTranslationResult(null);
    setError(null);
    setErrorMetadata(null);
    setQualityGateError(null);
  };

  const handleQualityGateError = (errorDetails: QualityGateErrorDetails) => {
    setQualityGateError(errorDetails);
    setPendingFile(null);
    setPendingLanguage(null);
    setAppState('upload');
  };

  const MainApp = () => {
    return (
      <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
        <Header health={health} onLogoClick={handleNewTranslation} />

        {/* Main Content */}
        <main className="relative">
          {/* Subtle background gradient */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(16,185,129,0.08),transparent)]" />

          <div className="relative z-10 max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
            {/* Error State */}
            {appState === 'error' && (
              <div className="animate-fade-in max-w-5xl mx-auto">
                {errorMetadata?.isTermination ? (
                  <TerminationCard
                    message={error || 'Verarbeitung wurde gestoppt'}
                    reason={errorMetadata.reason as string | undefined}
                    step={errorMetadata.step as string | undefined}
                    onReset={handleNewTranslation}
                  />
                ) : (
                  <Card className="border-error-200/50 bg-gradient-to-br from-error-50/50 to-white shadow-medium">
                    <CardContent className="p-6 sm:p-8">
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
                          <AlertTriangle className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <h3 className="text-xl font-bold text-error-900 mb-2">
                            Verarbeitung fehlgeschlagen
                          </h3>
                          <p className="text-error-700 mb-6 leading-relaxed">{error}</p>
                          <Button variant="brand" onClick={handleNewTranslation}>
                            <Sparkles className="w-4 h-4" />
                            Neuen Versuch starten
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* Upload State */}
            {appState === 'upload' && (
              <div className="space-y-10 sm:space-y-14 lg:space-y-20">
                {/* Hero Section — split layout on desktop */}
                <div className="flex flex-col lg:flex-row lg:items-center lg:gap-12 xl:gap-16">
                  {/* Left: Heading + trust badges */}
                  <div className="lg:w-[55%] text-center lg:text-left space-y-5 sm:space-y-6 mb-8 lg:mb-0">
                    <h2 className="text-hero bg-gradient-to-r from-primary-900 via-brand-700 to-accent-700 bg-clip-text text-transparent px-2 lg:px-0">
                      Medizinische Dokumente
                      <br className="hidden sm:block" />
                      <span className="sm:hidden"> </span>
                      <span className="bg-gradient-to-r from-brand-600 to-accent-600 bg-clip-text text-transparent">
                        einfach verstehen
                      </span>
                    </h2>
                    <p className="text-lead max-w-xl mx-auto lg:mx-0 px-4 sm:px-0">
                      Verwandeln Sie komplexe Arztbriefe und medizinische Befunde in verständliche
                      Sprache. Schnell, sicher und DSGVO-konform.
                    </p>

                    {/* Trust badges */}
                    <div className="flex flex-col sm:flex-row justify-center lg:justify-start items-center sm:items-start gap-2 sm:gap-6 text-xs sm:text-sm">
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

                  {/* Right: Upload component */}
                  <div className="lg:w-[45%]">
                    <FileUpload
                      onStartProcessing={handleStartProcessing}
                      onUploadError={handleUploadError}
                      availableLanguages={availableLanguages}
                      languagesLoaded={languagesLoaded}
                      qualityGateError={qualityGateError}
                      onClearQualityGateError={() => setQualityGateError(null)}
                    />
                  </div>
                </div>

                {/* Feature Cards with shadcn Card */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
                  <Card className="text-center border-t-2 border-t-brand-500 hover:shadow-medium hover:-translate-y-1 transition-all duration-300">
                    <CardHeader className="pb-2 sm:pb-3">
                      <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex items-center justify-center mx-auto bg-gradient-to-br from-brand-500 to-brand-600 text-white shadow-soft">
                        <Shield className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                        Datenschutz first
                      </h3>
                      <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                        Keine Speicherung Ihrer Daten. Alle Informationen werden nach der
                        Übersetzung automatisch gelöscht.
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="text-center border-t-2 border-t-brand-500 hover:shadow-medium hover:-translate-y-1 transition-all duration-300">
                    <CardHeader className="pb-2 sm:pb-3">
                      <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex items-center justify-center mx-auto bg-gradient-to-br from-brand-500 to-brand-600 text-white shadow-soft">
                        <FileText className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                        Medizinisch präzise
                      </h3>
                      <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                        Speziell für medizinische Fachbegriffe und Dokumente entwickelt. Präzise
                        Übersetzungen ohne Informationsverlust.
                      </p>
                    </CardContent>
                  </Card>

                  <Card className="text-center border-t-2 border-t-brand-500 hover:shadow-medium hover:-translate-y-1 transition-all duration-300 sm:col-span-2 lg:col-span-1">
                    <CardHeader className="pb-2 sm:pb-3">
                      <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex items-center justify-center mx-auto bg-gradient-to-br from-brand-500 to-brand-600 text-white shadow-soft">
                        <Zap className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                        Blitzschnell
                      </h3>
                      <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                        Erhalten Sie in wenigen Sekunden eine verständliche Übersetzung Ihrer
                        medizinischen Dokumente.
                      </p>
                    </CardContent>
                  </Card>
                </div>

                {/* FAQ Section */}
                <div className="mt-8 sm:mt-12 lg:mt-16">
                  <FAQ />
                </div>
              </div>
            )}

            {/* Processing State (unified upload → processing) */}
            {appState === 'processing' && pendingFile && (
              <div className="animate-fade-in max-w-5xl mx-auto">
                <DocumentProcessor
                  file={pendingFile}
                  selectedLanguage={pendingLanguage}
                  onComplete={handleProcessingComplete}
                  onError={handleProcessingError}
                  onCancel={handleProcessingCancel}
                  onQualityGateError={handleQualityGateError}
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
