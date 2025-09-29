import React, { useState, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Stethoscope, Shield, AlertTriangle, Sparkles, FileText, Zap, Globe, ChevronDown, Search, Settings } from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import TranslationResult from './components/TranslationResult';
import EnhancedSettingsModal from './components/EnhancedSettingsModal';
import Footer from './components/Footer';
import FAQ from './components/FAQ';
import Impressum from './pages/Impressum';
import Datenschutz from './pages/Datenschutz';
import Nutzungsbedingungen from './pages/Nutzungsbedingungen';
import ApiService from './services/api';
import { UploadResponse, TranslationResult as TranslationData, HealthCheck, ProcessingOptions, SupportedLanguage } from './types/api';

type AppState = 'upload' | 'initializing' | 'processing' | 'result' | 'error';

function App() {
  const [appState, setAppState] = useState<AppState>('upload');
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [translationResult, setTranslationResult] = useState<TranslationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthCheck | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string | null>(null);
  const [availableLanguages, setAvailableLanguages] = useState<SupportedLanguage[]>([]);
  const [languagesLoaded, setLanguagesLoaded] = useState(false);
  const [showAllLanguages, setShowAllLanguages] = useState(false);
  const [languageSearchTerm, setLanguageSearchTerm] = useState('');
  const [showSettings, setShowSettings] = useState(false);

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

  const handleUploadSuccess = async (response: UploadResponse) => {
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
    setSelectedLanguage(null);
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

  const renderLanguageSelector = () => {
    if (!languagesLoaded) {
      return (
        <div className="space-y-3 sm:space-y-4">
          <label className="block text-xs sm:text-sm font-medium text-neutral-700 text-center">
            Übersetzung (optional)
          </label>
          {/* Skeleton that matches the final button layout */}
          <div className="flex flex-wrap gap-1.5 sm:gap-2 justify-center min-h-[40px]">
            {/* Skeleton buttons to prevent layout shift */}
            {[1, 2, 3, 4, 5].map((i) => (
              <div 
                key={i} 
                className="px-2 sm:px-3 py-1.5 sm:py-2 bg-neutral-100 rounded-md sm:rounded-lg animate-pulse"
                style={{ width: i === 1 ? '100px' : '60px', height: '32px' }}
              />
            ))}
          </div>
          <p className="text-xs text-neutral-500 px-2 sm:px-0 text-center opacity-0">
            {/* Invisible placeholder to maintain height */}
            Optional: Wählen Sie eine Sprache
          </p>
        </div>
      );
    }

    const popularLanguages = availableLanguages.filter(lang => lang.popular);
    const allLanguages = availableLanguages.filter(lang => 
      lang.name.toLowerCase().includes(languageSearchTerm.toLowerCase()) ||
      lang.code.toLowerCase().includes(languageSearchTerm.toLowerCase())
    );
    const selectedLanguageInfo = availableLanguages.find(lang => lang.code === selectedLanguage);

    return (
      <div className="space-y-3 sm:space-y-4">
        <label className="block text-xs sm:text-sm font-medium text-neutral-700 text-center">
          Übersetzung (optional)
        </label>
        
        {/* Popular language quick buttons - Mobile Optimized */}
        <div className="flex flex-wrap gap-1.5 sm:gap-2 justify-center">
          <button
            onClick={() => setSelectedLanguage(null)}
            className={`px-2 sm:px-3 py-1.5 sm:py-2 text-xs font-medium rounded-md sm:rounded-lg transition-all duration-200 ${
              !selectedLanguage
                ? 'bg-neutral-100 text-neutral-700 ring-2 ring-neutral-300'
                : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100'
            }`}
          >
            Nur vereinfachen
          </button>
          
          {popularLanguages.slice(0, 4).map((language) => (
            <button
              key={language.code}
              onClick={() => setSelectedLanguage(language.code === selectedLanguage ? null : language.code)}
              className={`px-2 sm:px-3 py-1.5 sm:py-2 text-xs font-medium rounded-md sm:rounded-lg transition-all duration-200 ${
                selectedLanguage === language.code
                  ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-300'
                  : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              {language.name}
            </button>
          ))}
          
          {/* "Mehr Sprachen" Button - Mobile Optimized */}
          <button
            onClick={() => setShowAllLanguages(!showAllLanguages)}
            className={`px-2 sm:px-3 py-1.5 sm:py-2 text-xs font-medium rounded-md sm:rounded-lg transition-all duration-200 flex items-center space-x-1 ${
              showAllLanguages
                ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-200'
                : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100 border border-neutral-200'
            }`}
          >
            <span className="hidden sm:inline">Mehr Sprachen</span>
            <span className="sm:hidden">Mehr</span>
            <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${
              showAllLanguages ? 'rotate-180' : ''
            }`} />
          </button>
        </div>

        {/* All Languages Dropdown */}
        {showAllLanguages && (
          <div className="animate-slide-down">
            <div className="border border-neutral-200 rounded-xl bg-white shadow-lg">
              {/* Search */}
              <div className="p-3 border-b border-neutral-100">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400" />
                  <input
                    type="text"
                    placeholder="Sprache suchen..."
                    value={languageSearchTerm}
                    onChange={(e) => setLanguageSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 text-sm border border-neutral-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                  />
                </div>
              </div>

              {/* Language Grid */}
              <div className="p-3 max-h-64 overflow-y-auto">
                <div className="grid grid-cols-2 gap-2">
                  {allLanguages.map((language) => (
                    <button
                      key={language.code}
                      onClick={() => {
                        setSelectedLanguage(language.code === selectedLanguage ? null : language.code);
                        setShowAllLanguages(false);
                        setLanguageSearchTerm('');
                      }}
                      className={`text-left px-3 py-2 text-sm rounded-lg transition-colors duration-150 ${
                        selectedLanguage === language.code
                          ? 'bg-brand-100 text-brand-700 font-medium'
                          : 'text-neutral-700 hover:bg-neutral-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="truncate">{language.name}</span>
                        <span className="text-xs text-neutral-500 font-mono ml-2">
                          {language.code}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
                
                {allLanguages.length === 0 && languageSearchTerm && (
                  <div className="text-center py-4 text-sm text-neutral-500">
                    Keine Sprachen gefunden für "{languageSearchTerm}"
                  </div>
                )}
              </div>
              
              {/* Footer Info */}
              <div className="px-3 py-2 border-t border-neutral-100 bg-neutral-50 text-xs text-neutral-500 text-center rounded-b-xl">
                {availableLanguages.length} Sprachen verfügbar
              </div>
            </div>
          </div>
        )}

        {/* Selected language info */}
        {selectedLanguage && selectedLanguageInfo && (
          <div className="flex items-center space-x-3 px-4 py-3 bg-brand-50 rounded-xl border border-brand-200">
            <Globe className="w-4 h-4 text-brand-600" />
            <span className="text-sm text-brand-700">
              <strong>Ausgewählt:</strong> {selectedLanguageInfo.name}
            </span>
            <button
              onClick={() => setSelectedLanguage(null)}
              className="ml-auto text-brand-600 hover:text-brand-700 text-sm font-medium"
            >
              ✕
            </button>
          </div>
        )}

        {/* Info text - Mobile Optimized */}
        <p className="text-xs text-neutral-500 px-2 sm:px-0 text-center">
          {selectedLanguage 
            ? 'Das Dokument wird zuerst vereinfacht und dann in die gewählte Sprache übersetzt.'
            : 'Optional: Wählen Sie eine Sprache, um das vereinfachte Ergebnis zusätzlich zu übersetzen.'
          }
        </p>
      </div>
    );
  };

  const MainApp = () => (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      {/* Header - Mobile Optimized */}
      <header className="sticky top-0 z-50 header-blur">
        <div className="max-w-5xl mx-auto px-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 sm:h-20">
            <button 
              onClick={handleNewTranslation}
              className="flex items-center space-x-2 sm:space-x-3 hover:opacity-80 transition-opacity"
            >
              <div className="hero-gradient p-2 sm:p-3 rounded-xl sm:rounded-2xl shadow-soft">
                <Stethoscope className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
              </div>
              <div className="text-left">
                <h1 className="text-lg sm:text-2xl font-bold text-primary-900 tracking-tight">
                  HealthLingo
                </h1>
                <p className="text-xs sm:text-sm text-primary-600 font-medium">
                  Medizinische Dokumente verstehen
                </p>
              </div>
            </button>
            
            <div className="flex items-center space-x-4">
              {renderHealthIndicator()}
              <button
                onClick={() => setShowSettings(true)}
                className="p-2 text-primary-600 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-all duration-200 group"
                title="Prompt-Einstellungen"
              >
                <Settings className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </button>
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

        <div className="relative z-10 max-w-5xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
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
                    Verwandeln Sie komplexe Arztbriefe und medizinische Befunde in verständliche Sprache. 
                    <span className="hidden sm:inline">Schnell, sicher und DSGVO-konform.</span>
                    <span className="sm:hidden block mt-2">Schnell, sicher und DSGVO-konform.</span>
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
              
              {/* Language Selection */}
              <div>
                <div className="card-elevated">
                  <div className="card-body">
                    {renderLanguageSelector()}
                  </div>
                </div>
              </div>
              
              {/* Upload Component */}
              <div>
                <FileUpload
                  onUploadSuccess={handleUploadSuccess}
                  onUploadError={handleUploadError}
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
                    Keine Speicherung Ihrer Daten. Alle Informationen werden nach der 
                    Übersetzung automatisch gelöscht.
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
                    Speziell für medizinische Fachbegriffe und Dokumente entwickelt. 
                    Präzise Übersetzungen ohne Informationsverlust.
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
                    Erhalten Sie in wenigen Sekunden eine verständliche Übersetzung 
                    Ihrer medizinischen Dokumente.
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
                      <p className="text-primary-600">
                        Ihr Dokument wird vorbereitet...
                      </p>
                    </div>
                    
                    {/* Loading dots */}
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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
      
      {/* Settings Modal */}
      <EnhancedSettingsModal 
        isOpen={showSettings} 
        onClose={() => setShowSettings(false)} 
      />
    </div>
  );

  return (
    <Routes>
      <Route path="/" element={<MainApp />} />
      <Route path="/impressum" element={<Impressum />} />
      <Route path="/datenschutz" element={<Datenschutz />} />
      <Route path="/nutzungsbedingungen" element={<Nutzungsbedingungen />} />
    </Routes>
  );
}

export default App; 