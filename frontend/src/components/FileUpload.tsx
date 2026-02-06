import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  X,
  FileText,
  Image,
  AlertCircle,
  Play,
  Shield,
  Camera,
  Lightbulb,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Search,
  Globe,
  ScanLine,
  Check,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ApiService from '../services/api';
import { QualityGateErrorDetails, SupportedLanguage } from '../types/api';
import { useMobileDetect } from '../hooks/useMobileDetect';
import DocumentScanner from './DocumentScanner';

interface FileUploadProps {
  onStartProcessing: (file: File, language: string | null, sourceLanguage: 'de' | 'en') => void;
  onUploadError: (error: string) => void;
  disabled?: boolean;
  availableLanguages: SupportedLanguage[];
  languagesLoaded: boolean;
  qualityGateError?: QualityGateErrorDetails | null;
  onClearQualityGateError?: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onStartProcessing,
  onUploadError,
  disabled = false,
  availableLanguages,
  languagesLoaded,
  qualityGateError: externalQualityGateError,
  onClearQualityGateError,
}) => {
  const { t, i18n } = useTranslation();

  // Default source language based on UI language (German user = German document, English user = English document)
  const getDefaultSourceLanguage = (): 'de' | 'en' => {
    const uiLang = i18n.language?.substring(0, 2);
    return uiLang === 'en' ? 'en' : 'de';
  };

  const [selectedLanguage, setSelectedLanguage] = useState<string | null>(null);
  const [sourceLanguage, setSourceLanguage] = useState<'de' | 'en'>(getDefaultSourceLanguage);
  const [showAllLanguages, setShowAllLanguages] = useState(false);
  const [languageSearchTerm, setLanguageSearchTerm] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4>(1);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const privacyCheckboxRef = useRef<HTMLDivElement>(null);
  const { shouldShowScanner } = useMobileDetect();

  const qualityGateError = externalQualityGateError || null;

  // Helper function to translate quality issues using i18n
  const translateIssue = (issue: string): string => {
    const key = `qualityGate.issues.${issue}`;
    const translated = t(key);
    return translated === key ? issue : translated;
  };

  const handleFileUpload = useCallback(
    async (files: File[]) => {
      setValidationError(null);
      onClearQualityGateError?.();

      // Validate all files
      for (const file of files) {
        const validation = ApiService.validateFile(file);
        if (!validation.valid) {
          setValidationError(validation.error!);
          onUploadError(validation.error!);
          return;
        }
      }

      // Add files to selected files
      setSelectedFiles(prev => [...prev, ...files]);

      // Scroll to privacy checkbox after a short delay to allow rendering
      setTimeout(() => {
        privacyCheckboxRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
        // Scroll up a bit after centering to reduce scroll distance
        setTimeout(() => {
          window.scrollBy({ top: -100, behavior: 'smooth' });
        }, 400);
      }, 300);
    },
    [onUploadError, onClearQualityGateError]
  );

  const handleScanCapture = useCallback(
    (file: File) => {
      setScannerOpen(false);
      handleFileUpload([file]);
    },
    [handleFileUpload]
  );

  const handleStartProcessing = useCallback(() => {
    if (selectedFiles.length === 0 || !privacyAccepted) return;

    setValidationError(null);

    // For now, process only the first file (backend doesn't support multiple files yet)
    const file = selectedFiles[0];

    // Reset state
    setSelectedFiles([]);
    setPrivacyAccepted(false);

    // Pass file, language, and source language to parent — upload happens in DocumentProcessor
    onStartProcessing(file, selectedLanguage, sourceLanguage);
  }, [selectedFiles, privacyAccepted, selectedLanguage, sourceLanguage, onStartProcessing]);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearAllFiles = useCallback(() => {
    setSelectedFiles([]);
    setPrivacyAccepted(false);
    setCurrentStep(1);
  }, []);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        handleFileUpload(acceptedFiles);
      }
    },
    [handleFileUpload]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: disabled,
    maxFiles: 10, // Allow up to 10 files
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    noClick: false,
    noKeyboard: false,
  });

  // Wizard step titles
  const stepLabels = [
    t('wizard.step1Label'),
    t('wizard.step2Label'),
    t('wizard.step3Label'),
    t('wizard.step4Label'),
  ];

  // Wizard Progress Indicator
  const WizardProgress = () => (
    <div className="mb-6">
      {/* Step title */}
      <h3 className="text-center text-lg font-semibold text-primary-900 mb-4">
        {currentStep === 1 && t('wizard.step1Title')}
        {currentStep === 2 && t('wizard.step2Title')}
        {currentStep === 3 && t('wizard.step3Title')}
        {currentStep === 4 && t('wizard.step4Title')}
      </h3>

      {/* Progress indicator */}
      <nav aria-label={t('wizard.progressLabel')}>
        <ol className="flex items-center justify-center">
          {[1, 2, 3, 4].map((step, index) => (
            <li key={step} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  aria-current={step === currentStep ? 'step' : undefined}
                  aria-label={`${t('wizard.step')} ${step}: ${stepLabels[index]}${step < currentStep ? ` - ${t('wizard.completed')}` : ''}`}
                  className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
                    step < currentStep
                      ? 'bg-success-500 text-white'
                      : step === currentStep
                        ? 'bg-brand-500 text-white shadow-glow'
                        : 'bg-neutral-200 text-neutral-500'
                  }`}
                >
                  {step < currentStep ? (
                    <Check className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
                  ) : (
                    step
                  )}
                </div>
                <span
                  aria-hidden="true"
                  className={`hidden sm:block mt-1 text-xs font-medium ${
                    step <= currentStep ? 'text-primary-700' : 'text-neutral-400'
                  }`}
                >
                  {stepLabels[index]}
                </span>
              </div>
              {index < 3 && (
                <div
                  aria-hidden="true"
                  className={`w-8 sm:w-12 h-1 mx-1 sm:mx-2 rounded-full transition-all duration-300 ${
                    step < currentStep ? 'bg-success-500' : 'bg-neutral-200'
                  }`}
                />
              )}
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );

  // Selection Summary for Step 4
  const SelectionSummary = () => (
    <div className="card-elevated mb-4">
      <div className="card-body space-y-3">
        <h4 className="font-semibold text-primary-900">{t('wizard.summary')}</h4>
        <div className="text-sm space-y-2">
          <div className="flex items-center justify-between py-2 border-b border-neutral-100">
            <span className="text-primary-600">{t('wizard.file')}</span>
            <span className="font-medium text-primary-900 truncate max-w-[200px]">
              {selectedFiles[0]?.name}
            </span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-neutral-100">
            <span className="text-primary-600">{t('wizard.sourceLanguage')}</span>
            <span className="font-medium text-primary-900">
              {sourceLanguage === 'de' ? `🇩🇪 ${t('upload.german')}` : `🇬🇧 ${t('upload.english')}`}
            </span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-primary-600">{t('wizard.targetLanguage')}</span>
            <span className="font-medium text-primary-900">
              {selectedLanguage
                ? t('languages.' + selectedLanguage, {
                    defaultValue: availableLanguages.find(l => l.code === selectedLanguage)?.name,
                  })
                : t('upload.simplifyOnly')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );

  // Navigation buttons component
  const NavigationButtons = ({
    showBack = true,
    showNext = true,
    nextLabel,
    onNext,
    onBack,
    nextDisabled = false,
    nextVariant = 'primary',
  }: {
    showBack?: boolean;
    showNext?: boolean;
    nextLabel?: string;
    onNext?: () => void;
    onBack?: () => void;
    nextDisabled?: boolean;
    nextVariant?: 'primary' | 'success';
  }) => (
    <div className="flex justify-between items-center mt-6 pt-4 border-t border-neutral-100">
      {showBack ? (
        <button
          onClick={onBack || (() => setCurrentStep((prev) => (prev > 1 ? (prev - 1) as 1 | 2 | 3 | 4 : prev)))}
          className="flex items-center space-x-2 px-4 py-2 text-primary-600 hover:text-primary-700 hover:bg-neutral-50 rounded-lg transition-all"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>{t('wizard.back')}</span>
        </button>
      ) : (
        <div />
      )}
      {showNext && (
        <button
          onClick={onNext || (() => setCurrentStep((prev) => (prev < 4 ? (prev + 1) as 1 | 2 | 3 | 4 : prev)))}
          disabled={nextDisabled}
          className={`flex items-center space-x-2 px-6 py-2.5 rounded-lg font-medium transition-all ${
            nextDisabled
              ? 'bg-neutral-200 text-neutral-400 cursor-not-allowed'
              : nextVariant === 'success'
                ? 'bg-success-500 hover:bg-success-600 text-white shadow-md hover:shadow-lg'
                : 'bg-brand-500 hover:bg-brand-600 text-white shadow-md hover:shadow-lg'
          }`}
        >
          <span>{nextLabel || t('wizard.next')}</span>
          {nextVariant !== 'success' && <ChevronRight className="w-4 h-4" />}
          {nextVariant === 'success' && <Play className="w-4 h-4" />}
        </button>
      )}
    </div>
  );

  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    if (extension === 'pdf') {
      return <FileText className="w-8 h-8 text-error-500" />;
    } else if (['jpg', 'jpeg', 'png'].includes(extension || '')) {
      return <Image className="w-8 h-8 text-accent-500" />;
    }
    return <FileText className="w-8 h-8 text-primary-500" />;
  };

  const handleClick = () => {
    if (fileInputRef.current && !disabled) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="space-y-6">
      {/* Document Scanner Overlay - always available */}
      <DocumentScanner
        isOpen={scannerOpen}
        onCapture={handleScanCapture}
        onClose={() => setScannerOpen(false)}
      />

      {/* Wizard Progress Indicator - shown when files are selected */}
      {selectedFiles.length > 0 && <WizardProgress />}

      {/* Step 1: Upload Document */}
      {(currentStep === 1 || selectedFiles.length === 0) && (
        <>
          {/* Upload Area */}
          <div
            {...getRootProps()}
            onClick={handleClick}
            className={`upload-area ${selectedFiles.length > 0 ? 'py-6 sm:py-8' : ''} ${isDragActive ? 'dragover' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <input {...getInputProps()} ref={fileInputRef} />

            <div
              className={`${selectedFiles.length > 0 ? 'space-y-3 sm:space-y-4' : 'space-y-4 sm:space-y-6'}`}
            >
              <div className="flex justify-center">
                <div
                  className={`group w-14 h-14 sm:w-16 sm:h-16 bg-gradient-to-br from-brand-500 to-brand-600 rounded-xl sm:rounded-2xl flex items-center justify-center transition-all duration-300 ${!disabled ? 'group-hover:scale-110 group-hover:shadow-glow' : ''}`}
                >
                  <Upload className="w-6 h-6 sm:w-8 sm:h-8 text-white transition-transform duration-300 group-hover:scale-110" />
                </div>
              </div>

              <div className="text-center space-y-2 sm:space-y-3">
                <h3 className="text-xl sm:text-2xl font-bold text-primary-900">
                  {isDragActive
                    ? t('upload.titleDragActive')
                    : selectedFiles.length > 0
                      ? t('upload.titleAddMore')
                      : t('upload.title')}
                </h3>

                <p className="text-primary-600 text-sm sm:text-base lg:text-lg leading-relaxed max-w-md mx-auto px-4 sm:px-0">
                  {isDragActive
                    ? t('upload.descriptionDragActive')
                    : selectedFiles.length > 0
                      ? t('upload.descriptionAddMore')
                      : t('upload.description')}
                </p>
              </div>

              {selectedFiles.length === 0 && (
                <div className="flex justify-center">
                  <div className="glass-effect px-4 sm:px-6 py-2 sm:py-3 rounded-lg sm:rounded-xl">
                    <div className="text-xs sm:text-sm text-primary-600 space-y-1 text-center">
                      <div className="font-semibold">{t('upload.supportedFormats')}</div>
                      <div className="flex flex-col sm:flex-row items-center justify-center sm:space-x-4 space-y-1 sm:space-y-0 text-xs">
                        <span className="flex items-center space-x-1">
                          <FileText className="w-3 h-3 text-error-500" />
                          <span>PDF</span>
                        </span>
                        <span className="flex items-center space-x-1">
                          <Image className="w-3 h-3 text-accent-500" />
                          <span>JPG, PNG</span>
                        </span>
                        <span className="text-primary-400">{t('upload.maxSize')}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Scan Button (mobile/tablet) - shown when no files selected */}
          {shouldShowScanner && selectedFiles.length === 0 && (
            <div className="flex justify-center mt-2">
              <button
                onClick={() => setScannerOpen(true)}
                disabled={disabled}
                className="flex items-center justify-center gap-3 w-full max-w-md px-8 py-5 bg-gradient-to-r from-brand-500 via-brand-600 to-brand-700 text-white rounded-2xl font-bold text-lg shadow-xl hover:shadow-2xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed border-2 border-brand-400/30"
              >
                <ScanLine className="w-7 h-7" />
                <span>{t('upload.scanDocument')}</span>
              </button>
            </div>
          )}

          {/* Scan More Button (mobile/tablet) - shown when files are already selected */}
          {shouldShowScanner && selectedFiles.length > 0 && (
            <div className="flex justify-center">
              <button
                onClick={() => setScannerOpen(true)}
                disabled={disabled}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-brand-500 to-brand-600 text-white rounded-xl font-semibold text-base shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ScanLine className="w-5 h-5" />
                <span>{t('upload.scanMore')}</span>
              </button>
            </div>
          )}

          {/* Selected Files List (Step 1) */}
          {selectedFiles.length > 0 && (
            <div className="card-elevated">
              <div className="card-body">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-semibold text-primary-900">
                    {t('upload.selectedFiles', { count: selectedFiles.length })}
                  </h4>
                  <button
                    onClick={clearAllFiles}
                    className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                  >
                    {t('upload.removeAll')}
                  </button>
                </div>

                <div className="space-y-2">
                  {selectedFiles.map((file, index) => (
                    <div
                      key={`${file.name}-${index}`}
                      className="flex items-center space-x-3 p-3 bg-neutral-50 rounded-lg border border-neutral-200"
                    >
                      <div className="flex-shrink-0">{getFileIcon(file.name)}</div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-primary-900 truncate">{file.name}</p>
                        <p className="text-xs text-primary-500">
                          {ApiService.formatFileSize(file.size)}
                        </p>
                      </div>
                      <button
                        onClick={() => removeFile(index)}
                        aria-label={t('upload.removeFile', { fileName: file.name })}
                        className="flex-shrink-0 p-1 text-primary-400 hover:text-primary-600 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>

                <NavigationButtons
                  showBack={false}
                  showNext={selectedFiles.length > 0}
                  onNext={() => setCurrentStep(2)}
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* Step 2: Document Source Language */}
      {currentStep === 2 && selectedFiles.length > 0 && (
        <div className="card-elevated animate-slide-up">
          <div className="card-body">
            <div className="space-y-4 sm:space-y-6">
              <p className="text-sm text-primary-600 text-center">
                {t('upload.documentLanguageHint')}
              </p>

              <div className="flex gap-4 justify-center">
                <button
                  type="button"
                  onClick={() => setSourceLanguage('de')}
                  aria-pressed={sourceLanguage === 'de'}
                  className={`flex-1 max-w-[160px] px-6 py-4 rounded-xl font-medium transition-all flex flex-col items-center space-y-2 ${
                    sourceLanguage === 'de'
                      ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-400 shadow-md'
                      : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100 border border-neutral-200'
                  }`}
                >
                  <span className="text-3xl">🇩🇪</span>
                  <span className="text-base">{t('upload.german')}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSourceLanguage('en')}
                  aria-pressed={sourceLanguage === 'en'}
                  className={`flex-1 max-w-[160px] px-6 py-4 rounded-xl font-medium transition-all flex flex-col items-center space-y-2 ${
                    sourceLanguage === 'en'
                      ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-400 shadow-md'
                      : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100 border border-neutral-200'
                  }`}
                >
                  <span className="text-3xl">🇬🇧</span>
                  <span className="text-base">{t('upload.english')}</span>
                </button>
              </div>
            </div>

            <NavigationButtons
              showBack={true}
              showNext={true}
              onBack={() => setCurrentStep(1)}
              onNext={() => setCurrentStep(3)}
            />
          </div>
        </div>
      )}

      {/* Step 3: Target Language (Optional Translation) */}
      {currentStep === 3 && selectedFiles.length > 0 && (
        <div className="card-elevated animate-slide-up">
          <div className="card-body">
            {!languagesLoaded ? (
              <div className="space-y-3 sm:space-y-4">
                <div className="flex flex-wrap gap-1.5 sm:gap-2 justify-center min-h-[40px]">
                  {[1, 2, 3, 4, 5].map(i => (
                    <div
                      key={i}
                      className="px-2 sm:px-3 py-1.5 sm:py-2 bg-neutral-100 rounded-md sm:rounded-lg animate-pulse"
                      style={{ width: i === 1 ? '100px' : '60px', height: '32px' }}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4 sm:space-y-5">
                <p className="text-sm text-primary-600 text-center">
                  {t('wizard.step3Hint')}
                </p>

                <div className="flex flex-wrap gap-2 sm:gap-3 justify-center">
                  <button
                    onClick={() => setSelectedLanguage(null)}
                    aria-pressed={!selectedLanguage}
                    className={`px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                      !selectedLanguage
                        ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-300 shadow-sm'
                        : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100 border border-neutral-200'
                    }`}
                  >
                    {t('upload.simplifyOnly')}
                  </button>

                  {availableLanguages
                    .filter(lang => lang.popular && lang.code !== i18n.language?.substring(0, 2))
                    .slice(0, 4)
                    .map(language => (
                      <button
                        key={language.code}
                        onClick={() =>
                          setSelectedLanguage(
                            language.code === selectedLanguage ? null : language.code
                          )
                        }
                        aria-pressed={selectedLanguage === language.code}
                        className={`px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 ${
                          selectedLanguage === language.code
                            ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-300 shadow-sm'
                            : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100 border border-neutral-200'
                        }`}
                      >
                        {t('languages.' + language.code, { defaultValue: language.name })}
                      </button>
                    ))}

                  <button
                    onClick={() => setShowAllLanguages(!showAllLanguages)}
                    aria-expanded={showAllLanguages}
                    className={`px-4 py-2.5 text-sm font-medium rounded-lg transition-all duration-200 flex items-center space-x-1 ${
                      showAllLanguages
                        ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-200'
                        : 'bg-neutral-50 text-neutral-600 hover:bg-neutral-100 border border-neutral-200'
                    }`}
                  >
                    <span className="hidden sm:inline">{t('upload.moreLanguages')}</span>
                    <span className="sm:hidden">{t('upload.more')}</span>
                    <ChevronDown
                      className={`w-3 h-3 transition-transform duration-200 ${
                        showAllLanguages ? 'rotate-180' : ''
                      }`}
                    />
                  </button>
                </div>

                {showAllLanguages && (
                  <div className="animate-slide-down">
                    <div className="border border-neutral-200 rounded-xl bg-white shadow-lg">
                      <div className="p-3 border-b border-neutral-100">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400" />
                          <input
                            type="text"
                            id="language-search"
                            aria-label={t('upload.searchLanguage')}
                            placeholder={t('upload.searchLanguage')}
                            value={languageSearchTerm}
                            onChange={e => setLanguageSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 text-sm border border-neutral-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                          />
                        </div>
                      </div>

                      <div className="p-3 max-h-64 overflow-y-auto">
                        <div className="grid grid-cols-2 gap-2">
                          {availableLanguages
                            .filter(lang => lang.code !== i18n.language?.substring(0, 2))
                            .filter(
                              lang =>
                                lang.name
                                  .toLowerCase()
                                  .includes(languageSearchTerm.toLowerCase()) ||
                                lang.code.toLowerCase().includes(languageSearchTerm.toLowerCase())
                            )
                            .map(language => (
                              <button
                                key={language.code}
                                onClick={() => {
                                  setSelectedLanguage(
                                    language.code === selectedLanguage ? null : language.code
                                  );
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
                                  <span className="truncate">{t('languages.' + language.code, { defaultValue: language.name })}</span>
                                  <span className="text-xs text-neutral-500 font-mono ml-2">
                                    {language.code}
                                  </span>
                                </div>
                              </button>
                            ))}
                        </div>

                        {availableLanguages
                          .filter(lang => lang.code !== i18n.language?.substring(0, 2))
                          .filter(
                            lang =>
                              lang.name.toLowerCase().includes(languageSearchTerm.toLowerCase()) ||
                              lang.code.toLowerCase().includes(languageSearchTerm.toLowerCase())
                          ).length === 0 &&
                          languageSearchTerm && (
                            <div role="alert" aria-live="polite" className="text-center py-4 text-sm text-neutral-500">
                              {t('upload.noLanguagesFound', { term: languageSearchTerm })}
                            </div>
                          )}
                      </div>

                      <div className="px-3 py-2 border-t border-neutral-100 bg-neutral-50 text-xs text-neutral-500 text-center rounded-b-xl">
                        {t('upload.languagesAvailable', { count: availableLanguages.length })}
                      </div>
                    </div>
                  </div>
                )}

                {selectedLanguage && (
                  <div className="flex items-center space-x-3 px-4 py-3 bg-brand-50 rounded-xl border border-brand-200">
                    <Globe className="w-4 h-4 text-brand-600" />
                    <span className="text-sm text-brand-700">
                      <strong>{t('upload.selected')}</strong>{' '}
                      {t('languages.' + (availableLanguages.find(lang => lang.code === selectedLanguage)?.code || ''), { defaultValue: availableLanguages.find(lang => lang.code === selectedLanguage)?.name })}
                    </span>
                    <button
                      onClick={() => setSelectedLanguage(null)}
                      aria-label={t('upload.clearLanguageSelection')}
                      className="ml-auto text-brand-600 hover:text-brand-700 text-sm font-medium"
                    >
                      ✕
                    </button>
                  </div>
                )}

                <p className="text-xs text-neutral-500 px-2 sm:px-0 text-center">
                  {selectedLanguage
                    ? t('upload.translationHintSelected')
                    : t('upload.translationHintOptional')}
                </p>
              </div>
            )}

            <NavigationButtons
              showBack={true}
              showNext={true}
              onBack={() => setCurrentStep(2)}
              onNext={() => setCurrentStep(4)}
            />
          </div>
        </div>
      )}

      {/* Step 4: Consent & Start */}
      {currentStep === 4 && selectedFiles.length > 0 && (
        <div className="space-y-4 animate-slide-up">
          {/* Selection Summary */}
          <SelectionSummary />

          {/* Privacy Policy Checkbox */}
          <div
            ref={privacyCheckboxRef}
            className={`card-elevated transition-all duration-300 ${
              !privacyAccepted
                ? 'ring-2 ring-amber-400 ring-offset-2 shadow-[0_0_15px_rgba(251,191,36,0.3)]'
                : 'ring-2 ring-success-400 ring-offset-2'
            }`}
          >
            <div className="card-body">
              {/* Header with status indicator */}
              <div
                className={`flex items-center space-x-2 mb-3 pb-3 border-b ${
                  privacyAccepted ? 'border-success-200' : 'border-amber-200'
                }`}
              >
                <div
                  className={`p-1.5 rounded-lg ${
                    privacyAccepted ? 'bg-success-100' : 'bg-amber-100 animate-pulse'
                  }`}
                >
                  {privacyAccepted ? (
                    <Shield className="w-4 h-4 text-success-600" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                  )}
                </div>
                <span
                  className={`text-sm font-semibold ${
                    privacyAccepted ? 'text-success-700' : 'text-amber-700'
                  }`}
                >
                  {privacyAccepted ? t('upload.privacyConfirmed') : t('upload.pleaseConfirm')}
                </span>
              </div>

              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 pt-0.5">
                  <input
                    type="checkbox"
                    id="privacy-checkbox"
                    checked={privacyAccepted}
                    onChange={e => setPrivacyAccepted(e.target.checked)}
                    className={`w-5 h-5 rounded focus:ring-2 transition-colors ${
                      privacyAccepted
                        ? 'text-success-600 bg-success-50 border-success-300 focus:ring-success-500'
                        : 'text-brand-600 bg-amber-50 border-amber-300 focus:ring-amber-500'
                    }`}
                  />
                </div>
                <div className="flex-1">
                  <label
                    htmlFor="privacy-checkbox"
                    className="text-sm text-primary-700 cursor-pointer"
                  >
                    {t('upload.privacyConsentPrefix')}{' '}
                    <Link
                      to="/datenschutz"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`${t('upload.privacyPolicy')} (${t('accessibility.opensInNewTab')})`}
                      className="text-brand-600 hover:text-brand-700 underline font-medium"
                    >
                      {t('upload.privacyPolicy')}
                    </Link>{' '}
                    {t('upload.privacyConsentSuffix')}
                  </label>
                </div>
              </div>

              <NavigationButtons
                showBack={true}
                showNext={true}
                onBack={() => setCurrentStep(3)}
                onNext={handleStartProcessing}
                nextLabel={t('upload.startProcessing')}
                nextDisabled={!privacyAccepted}
                nextVariant="success"
              />
            </div>
          </div>
        </div>
      )}

      {/* Quality Gate Error - Special Display */}
      {qualityGateError && (
        <div className="card-elevated border-amber-200/50 bg-gradient-to-br from-amber-50/50 to-white animate-slide-up">
          <div className="card-body space-y-4">
            {/* Header */}
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl flex items-center justify-center">
                <Camera className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-amber-900 mb-1 text-lg">
                  {t('qualityGate.title')}
                </h4>
                <p className="text-amber-700 text-sm leading-relaxed">
                  {t('qualityGate.description')}
                </p>
              </div>
            </div>

            {/* Quality Score */}
            <div className="glass-effect p-3 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <span className="text-primary-600 font-medium">{t('qualityGate.qualityScore')}</span>
                <span className="font-semibold text-primary-900">
                  {(qualityGateError.details.confidence_score * 100).toFixed(0)}%
                  <span className="text-primary-500 font-normal">
                    {' '}
                    / {(qualityGateError.details.min_threshold * 100).toFixed(0)}% {t('qualityGate.required')}
                  </span>
                </span>
              </div>
              <div
                role="progressbar"
                aria-valuenow={Math.round(qualityGateError.details.confidence_score * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={t('qualityGate.qualityScore')}
                className="mt-2 w-full bg-neutral-200 rounded-full h-2 overflow-hidden"
              >
                <div
                  className="h-full bg-gradient-to-r from-amber-400 to-amber-600 rounded-full transition-all duration-500"
                  style={{ width: `${qualityGateError.details.confidence_score * 100}%` }}
                />
              </div>
            </div>

            {/* Issues */}
            {qualityGateError.details.issues && qualityGateError.details.issues.length > 0 && (
              <div className="space-y-2">
                <h5 className="text-sm font-semibold text-primary-900 flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-amber-600" />
                  <span>{t('qualityGate.detectedIssues')}</span>
                </h5>
                <ul className="space-y-1.5">
                  {qualityGateError.details.issues.map((issue, index) => (
                    <li key={index} className="text-sm text-primary-700 flex items-start space-x-2">
                      <span className="text-amber-500 mt-0.5">•</span>
                      <span>{translateIssue(issue)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Suggestions */}
            {qualityGateError.details.suggestions &&
              qualityGateError.details.suggestions.length > 0 && (
                <div className="space-y-3 bg-gradient-to-br from-accent-50/50 to-transparent p-4 rounded-lg border border-accent-200/50">
                  <h5 className="text-sm font-semibold text-primary-900 flex items-center space-x-2">
                    <Lightbulb className="w-4 h-4 text-accent-600" />
                    <span>{t('qualityGate.improvementTips')}</span>
                  </h5>
                  <ul className="space-y-2">
                    {qualityGateError.details.suggestions.map((suggestion, index) => (
                      <li
                        key={index}
                        className="text-sm text-primary-700 flex items-start space-x-2.5"
                      >
                        <span className="text-accent-600 font-bold mt-0.5">{index + 1}.</span>
                        <span className="leading-relaxed">{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {/* Try Again Button */}
            <div className="pt-2">
              <button
                onClick={() => {
                  onClearQualityGateError?.();
                  setSelectedFiles([]);
                  setPrivacyAccepted(false);
                  if (fileInputRef.current) {
                    fileInputRef.current.value = '';
                  }
                }}
                className="w-full btn-secondary text-sm py-2.5"
              >
                {t('qualityGate.retakePhoto')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Regular Validation Error */}
      {validationError && !qualityGateError && (
        <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white animate-slide-up">
          <div className="card-compact">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-error-500 to-error-600 rounded-xl flex items-center justify-center">
                <AlertCircle className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-error-900 mb-1">{t('upload.uploadFailed')}</h4>
                <p className="text-error-700 text-sm leading-relaxed">{validationError}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Success State (if needed) */}
      {!validationError && selectedFiles.length === 0 && (
        <div className="text-center">
          <p className="text-xs text-primary-500">
            {t('upload.gdprNotice')}
          </p>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
