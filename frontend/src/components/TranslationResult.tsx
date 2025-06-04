import React, { useState } from 'react';
import { Copy, Download, Eye, EyeOff, CheckCircle, FileText, Clock, Star, Sparkles, RefreshCw, ArrowLeft, Globe } from 'lucide-react';
import ApiService from '../services/api';
import { TranslationResult as TranslationData } from '../types/api';

interface TranslationResultProps {
  result: TranslationData;
  onNewTranslation: () => void;
}

const TranslationResult: React.FC<TranslationResultProps> = ({
  result,
  onNewTranslation
}) => {
  const [showOriginal, setShowOriginal] = useState(false);
  const [copiedText, setCopiedText] = useState<'original' | 'translated' | 'language' | null>(null);
  const [activeTab, setActiveTab] = useState<'simplified' | 'language'>('simplified');

  const handleCopy = async (text: string, type: 'original' | 'translated' | 'language') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedText(type);
      setTimeout(() => setCopiedText(null), 2000);
    } catch (error) {
      console.error('Copy failed:', error);
    }
  };

  const handleDownload = () => {
    const content = `Medizinische Dokumentenübersetzung
========================================

Dokumenttyp: ${result.document_type_detected}
Vertrauensgrad: ${(result.confidence_score * 100).toFixed(1)}%
${result.language_confidence_score ? `Übersetzungsqualität: ${(result.language_confidence_score * 100).toFixed(1)}%` : ''}
Verarbeitungszeit: ${ApiService.formatDuration(result.processing_time_seconds)}
Zeitstempel: ${new Date(result.timestamp).toLocaleString('de-DE')}
${result.target_language ? `Zielsprache: ${result.target_language}` : ''}

ÜBERSETZUNG IN EINFACHER SPRACHE:
${result.translated_text}

${result.language_translated_text && result.target_language ? `
ÜBERSETZUNG IN ${result.target_language.toUpperCase()}:
${result.language_translated_text}
` : ''}

${showOriginal ? `
ORIGINALTEXT:
${result.original_text}
` : ''}

Hinweis: Diese Übersetzung wurde automatisch erstellt und ersetzt nicht die professionelle medizinische Beratung.
`;

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `medizinische-uebersetzung-${Date.now()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-success-700 bg-success-100 ring-success-200';
    if (score >= 0.6) return 'text-warning-700 bg-warning-100 ring-warning-200';
    return 'text-error-700 bg-error-100 ring-error-200';
  };

  const getConfidenceText = (score: number) => {
    if (score >= 0.8) return 'Sehr gut';
    if (score >= 0.6) return 'Gut';
    return 'Überprüfen';
  };

  const getConfidenceIcon = (score: number) => {
    if (score >= 0.8) return '✨';
    if (score >= 0.6) return '⭐';
    return '⚠️';
  };

  // Bestimme die anzuzeigende Übersetzung basierend auf dem aktiven Tab
  const getDisplayedText = () => {
    if (activeTab === 'language' && result.language_translated_text) {
      return result.language_translated_text;
    }
    return result.translated_text;
  };

  const getDisplayedConfidence = () => {
    if (activeTab === 'language' && result.language_confidence_score) {
      return result.language_confidence_score;
    }
    return result.confidence_score;
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Hero Section */}
      <div className="text-center space-y-6">
        <div className="relative">
          <div className="w-20 h-20 bg-gradient-to-br from-success-500 via-brand-600 to-accent-600 rounded-3xl flex items-center justify-center mx-auto shadow-glow">
            <Sparkles className="w-10 h-10 text-white" />
          </div>
        </div>
        
        <div className="space-y-2">
          <h2 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary-900 via-brand-700 to-success-700 bg-clip-text text-transparent">
            Übersetzung abgeschlossen
          </h2>
          <p className="text-lg text-primary-600 max-w-2xl mx-auto">
            {result.language_translated_text 
              ? 'Ihr medizinisches Dokument wurde vereinfacht und übersetzt'
              : 'Ihr medizinisches Dokument wurde erfolgreich in verständliche Sprache übersetzt'
            }
          </p>
        </div>
      </div>

      {/* Metadata Cards */}
      <div className={`grid grid-cols-1 ${result.language_translated_text ? 'md:grid-cols-4' : 'md:grid-cols-3'} gap-6`}>
        {/* Dokumenttyp */}
        <div className="feature-card group">
          <div className="flex items-center space-x-4">
            <div className="feature-icon">
              <FileText className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-primary-600 mb-1">Dokumenttyp</div>
              <div className="font-bold text-primary-900 capitalize text-lg">
                {result.document_type_detected || 'Medizinisches Dokument'}
              </div>
            </div>
          </div>
        </div>

        {/* Vertrauensgrad */}
        <div className="feature-card group">
          <div className="flex items-center space-x-4">
            <div className="feature-icon">
              <Star className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-primary-600 mb-1">Qualität</div>
              <div className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-semibold ring-1 ring-inset ${getConfidenceColor(getDisplayedConfidence())}`}>
                <span className="mr-1">{getConfidenceIcon(getDisplayedConfidence())}</span>
                {getConfidenceText(getDisplayedConfidence())} ({(getDisplayedConfidence() * 100).toFixed(0)}%)
              </div>
            </div>
          </div>
        </div>

        {/* Sprache (nur wenn übersetzt) */}
        {result.language_translated_text && result.target_language && (
          <div className="feature-card group">
            <div className="flex items-center space-x-4">
              <div className="feature-icon">
                <Globe className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-primary-600 mb-1">Sprache</div>
                <div className="font-bold text-primary-900 text-lg">
                  {result.target_language.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Verarbeitungszeit */}
        <div className="feature-card group">
          <div className="flex items-center space-x-4">
            <div className="feature-icon">
              <Clock className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-primary-600 mb-1">Verarbeitungszeit</div>
              <div className="font-bold text-primary-900 text-lg">
                {ApiService.formatDuration(result.processing_time_seconds)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs für Sprachversionen (nur wenn Sprachübersetzung vorhanden) */}
      {result.language_translated_text && (
        <div className="flex justify-center">
          <div className="inline-flex bg-neutral-100 rounded-xl p-1">
            <button
              onClick={() => setActiveTab('simplified')}
              className={`px-6 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                activeTab === 'simplified'
                  ? 'bg-white text-brand-700 shadow-sm'
                  : 'text-neutral-600 hover:text-neutral-800'
              }`}
            >
              📄 Vereinfacht (Deutsch)
            </button>
            <button
              onClick={() => setActiveTab('language')}
              className={`px-6 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                activeTab === 'language'
                  ? 'bg-white text-brand-700 shadow-sm'
                  : 'text-neutral-600 hover:text-neutral-800'
              }`}
            >
              <Globe className="w-4 h-4 inline mr-2" />
              {result.target_language?.toUpperCase()}
            </button>
          </div>
        </div>
      )}

      {/* Main Translation Card */}
      <div className="card-elevated border-brand-200/50 bg-gradient-to-br from-brand-50/30 to-accent-50/30">
        <div className="card-body">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center space-x-4">
              <div className="w-14 h-14 bg-gradient-to-br from-brand-500 via-brand-600 to-accent-600 rounded-2xl flex items-center justify-center shadow-soft">
                {activeTab === 'language' ? (
                  <Globe className="w-7 h-7 text-white" />
                ) : (
                  <span className="text-2xl">📄</span>
                )}
              </div>
              <div>
                <h3 className="text-2xl font-bold text-primary-900">
                  {activeTab === 'language' 
                    ? `Übersetzung (${result.target_language?.toUpperCase()})`
                    : 'Verständliche Übersetzung'
                  }
                </h3>
                <p className="text-primary-600">
                  {activeTab === 'language'
                    ? `Ihr Dokument in ${result.target_language}`
                    : 'Ihr Dokument in einfacher Sprache erklärt'
                  }
                </p>
              </div>
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={() => handleCopy(getDisplayedText(), activeTab === 'language' ? 'language' : 'translated')}
                className="btn-secondary group"
                disabled={copiedText === (activeTab === 'language' ? 'language' : 'translated')}
              >
                {copiedText === (activeTab === 'language' ? 'language' : 'translated') ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-success-600" />
                    <span className="text-success-600 ml-2">Kopiert!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
                    <span className="ml-2">Kopieren</span>
                  </>
                )}
              </button>
              
              <button
                onClick={handleDownload}
                className="btn-primary group"
              >
                <Download className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
                <span className="ml-2">Download</span>
              </button>
            </div>
          </div>

          {/* Translation Content */}
          <div className="relative">
            <div className="glass-card p-8 md:p-10">
              <div className="medical-text-formatted text-primary-800 leading-relaxed whitespace-pre-wrap">
                {getDisplayedText()}
              </div>
            </div>
            
            {/* Decorative elements */}
            <div className="absolute -top-2 -left-2 w-6 h-6 bg-gradient-to-br from-brand-400 to-brand-500 rounded-full opacity-60"></div>
            <div className="absolute -bottom-2 -right-2 w-4 h-4 bg-gradient-to-br from-accent-400 to-accent-500 rounded-full opacity-60"></div>
          </div>

          {/* Quality indicator */}
          <div className="mt-6 glass-effect p-4 rounded-xl">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center space-x-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${getConfidenceColor(getDisplayedConfidence())}`}>
                  <Star className="w-4 h-4" />
                </div>
                <div>
                  <span className="font-medium text-primary-700">
                    {activeTab === 'language' ? 'Übersetzungsqualität' : 'Vereinfachungsqualität'}: <span className="font-bold">{getConfidenceText(getDisplayedConfidence())}</span>
                  </span>
                  <div className="text-xs text-primary-500">
                    Vertrauen: {(getDisplayedConfidence() * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-primary-500 mb-1">Verarbeitet in</div>
                <div className="font-semibold text-primary-700">
                  {ApiService.formatDuration(result.processing_time_seconds)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Original Text Section */}
      <div className="card-elevated">
        <div className="card-body">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-xl font-bold text-primary-900">
                Originaltext
              </h3>
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={() => setShowOriginal(!showOriginal)}
                className="btn-secondary group"
              >
                {showOriginal ? (
                  <>
                    <EyeOff className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
                    <span className="ml-2">Ausblenden</span>
                  </>
                ) : (
                  <>
                    <Eye className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
                    <span className="ml-2">Anzeigen</span>
                  </>
                )}
              </button>
              
              {showOriginal && (
                <button
                  onClick={() => handleCopy(result.original_text, 'original')}
                  className="btn-ghost group"
                  disabled={copiedText === 'original'}
                >
                  {copiedText === 'original' ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-success-600" />
                      <span className="text-success-600 ml-2">Kopiert!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 transition-transform duration-200 group-hover:scale-110" />
                      <span className="ml-2">Kopieren</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {showOriginal && (
            <div className="animate-slide-down">
              <div className="text-result bg-gradient-to-br from-neutral-50 to-primary-50/30">
                {result.original_text}
              </div>
            </div>
          )}
          
          {!showOriginal && (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Eye className="w-8 h-8 text-primary-500" />
              </div>
              <p className="text-primary-600">
                Klicken Sie auf "Anzeigen", um den Originaltext zu sehen
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center pt-6">
        <button
          onClick={onNewTranslation}
          className="btn-primary group flex-1 sm:flex-none"
        >
          <RefreshCw className="w-5 h-5 transition-transform duration-200 group-hover:rotate-180" />
          <span className="ml-2">Neues Dokument übersetzen</span>
        </button>
        
        <button
          onClick={handleDownload}
          className="btn-secondary group flex-1 sm:flex-none"
        >
          <Download className="w-5 h-5 transition-transform duration-200 group-hover:scale-110" />
          <span className="ml-2">Als Textdatei speichern</span>
        </button>
      </div>

      {/* Disclaimer */}
      <div className="glass-effect p-6 rounded-2xl border border-warning-200/50 bg-gradient-to-br from-warning-50/30 to-orange-50/30">
        <div className="flex items-start space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-warning-400 to-warning-500 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-white text-sm">⚠️</span>
          </div>
          <div>
            <h4 className="font-semibold text-warning-900 mb-2">Wichtiger Hinweis</h4>
            <p className="text-warning-800 text-sm leading-relaxed">
              Diese Übersetzung wurde automatisch erstellt und dient nur zur Orientierung. 
              Sie ersetzt nicht die professionelle medizinische Beratung, Diagnose oder Behandlung. 
              Wenden Sie sich bei Fragen immer an Ihren Arzt oder andere qualifizierte Gesundheitsdienstleister.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranslationResult; 