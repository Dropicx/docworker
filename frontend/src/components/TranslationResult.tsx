import React, { useState, useEffect, useCallback } from 'react';
import {
  Copy,
  Download,
  Eye,
  EyeOff,
  CheckCircle,
  FileText,
  Clock,
  Sparkles,
  RefreshCw,
  Globe,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ReactDOM from 'react-dom/client';
import ApiService from '../services/api';
import { TranslationResult as TranslationData } from '../types/api';
import { exportToPDF } from '../utils/pdfExportAdvanced';
import { useAuth } from '../contexts/AuthContext';
import FeedbackWidget from './FeedbackWidget';
import { feedbackApi } from '../services/feedbackApi';

interface TranslationResultProps {
  result: TranslationData;
  onNewTranslation: () => void;
}

const TranslationResult: React.FC<TranslationResultProps> = ({ result, onNewTranslation }) => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [showOriginal, setShowOriginal] = useState(false);
  const [copiedText, setCopiedText] = useState<'original' | 'translated' | 'language' | null>(null);
  // Wenn eine Sprachübersetzung vorhanden ist, zeige direkt den Sprach-Tab
  const [activeTab, setActiveTab] = useState<'simplified' | 'language'>(
    result.language_translated_text ? 'language' : 'simplified'
  );
  // Track if feedback was submitted (Issue #47)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  // Handle cleanup when "Neue Übersetzung" is clicked without feedback (Issue #47)
  const handleNewTranslation = useCallback(() => {
    if (!feedbackSubmitted) {
      // Cleanup content since user is leaving without feedback
      feedbackApi.cleanupContent(result.processing_id);
    }
    onNewTranslation();
  }, [feedbackSubmitted, result.processing_id, onNewTranslation]);

  // Cleanup on unmount if feedback wasn't submitted (Issue #47)
  useEffect(() => {
    return () => {
      // Note: The FeedbackWidget also handles beforeunload cleanup
      // This is a safety net for programmatic navigation
      if (!feedbackSubmitted) {
        feedbackApi.cleanupContent(result.processing_id);
      }
    };
  }, [feedbackSubmitted, result.processing_id]);

  const handleCopy = async (text: string, type: 'original' | 'translated' | 'language') => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedText(type);
      setTimeout(() => setCopiedText(null), 2000);
    } catch (error) {
      console.error('Copy failed:', error);
    }
  };

  const handleDownload = async () => {
    try {
      // Bestimme welcher Text exportiert werden soll
      const textToExport = getDisplayedText();
      const isLanguageExport = activeTab === 'language' && result.language_translated_text;

      // Generiere Dateinamen
      const timestamp = new Date().toISOString().split('T')[0];
      const languageSuffix = isLanguageExport ? `_${result.target_language}` : '_DE';
      const filename = `medizinische_uebersetzung_${timestamp}${languageSuffix}.pdf`;

      // Erstelle temporäres Element mit PDF-Version des Texts
      const tempDiv = document.createElement('div');
      tempDiv.id = 'pdf-export-content-temp';
      tempDiv.style.position = 'absolute';
      tempDiv.style.left = '-9999px';
      tempDiv.className = 'markdown-content';
      document.body.appendChild(tempDiv);

      // Rendere ReactMarkdown in das temporäre Element
      const root = ReactDOM.createRoot(tempDiv);
      root.render(
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => <h1>{children}</h1>,
            h2: ({ children }) => <h2>{children}</h2>,
            h3: ({ children }) => <h3>{children}</h3>,
            p: ({ children }) => <p>{children}</p>,
            ul: ({ children }) => <ul>{children}</ul>,
            li: ({ children }) => <li>{children}</li>,
            strong: ({ children }) => <strong>{children}</strong>,
          }}
        >
          {textToExport}
        </ReactMarkdown>
      );

      // Warte kurz auf das Rendering
      setTimeout(async () => {
        // Exportiere als PDF
        await exportToPDF('pdf-export-content-temp', filename, {
          title: isLanguageExport
            ? `Übersetzung (${result.target_language?.toUpperCase()})`
            : 'Verständliche Übersetzung',
          content: textToExport,
          isTranslation: true,
          language: isLanguageExport ? result.target_language : 'Deutsch',
          processingTime: result.processing_time_seconds,
          documentType: result.document_type_detected,
        });

        // Cleanup
        root.unmount();
        document.body.removeChild(tempDiv);
      }, 200);
    } catch (error) {
      console.error('PDF Export failed:', error);
      alert('PDF-Export fehlgeschlagen. Bitte versuchen Sie es erneut.');
    }
  };

  const _getConfidenceColor = (score: number) => {
    if (score >= 0.8) return 'text-success-700 bg-success-100 ring-success-200';
    if (score >= 0.6) return 'text-warning-700 bg-warning-100 ring-warning-200';
    return 'text-error-700 bg-error-100 ring-error-200';
  };

  const _getConfidenceText = (score: number) => {
    if (score >= 0.8) return 'Sehr gut';
    if (score >= 0.6) return 'Gut';
    return 'Überprüfen';
  };

  const _getConfidenceIcon = (score: number) => {
    if (score >= 0.8) return '✨';
    if (score >= 0.6) return '⭐';
    return '⚠️';
  };

  // Clean up markdown formatting issues from AI output
  const cleanMarkdownOutput = (text: string): string => {
    if (!text) return text;

    let cleaned = text;

    // Remove ALL code fences (``` or ```language) anywhere in the text
    // Handles: ```markdown, ```md, ```text, ``` etc.
    cleaned = cleaned.replace(/```[\w]*\s*\n?/g, '');

    // Remove any remaining standalone ``` lines
    cleaned = cleaned.replace(/^```\s*$/gm, '');

    // CRITICAL: Remove 4+ leading spaces from ALL lines to prevent code block rendering
    // Markdown interprets 4+ leading spaces as code blocks
    // Preserve up to 3 spaces for nested lists, remove the rest
    cleaned = cleaned.replace(/^(\s{4,})/gm, (match) => {
      // Keep max 2 spaces for nesting, remove excessive indentation
      return '  ';
    });

    // Also handle tab characters which can trigger code blocks
    cleaned = cleaned.replace(/^\t+/gm, '');

    // Fix doubled markdown headers: "## ## Header" -> "## Header"
    cleaned = cleaned.replace(/^(#{1,6})\s+\1\s+/gm, '$1 ');

    // Fix tripled headers just in case
    cleaned = cleaned.replace(/^(#{1,6})\s+\1\s+\1\s+/gm, '$1 ');

    // Convert <br> and <br/> tags to actual newlines
    cleaned = cleaned.replace(/<br\s*\/?>/gi, '\n');

    return cleaned.trim();
  };

  // Bestimme die anzuzeigende Übersetzung basierend auf dem aktiven Tab
  const getDisplayedText = () => {
    let text = '';
    if (activeTab === 'language' && result.language_translated_text) {
      text = result.language_translated_text;
    } else {
      text = result.translated_text;
    }
    return cleanMarkdownOutput(text);
  };

  const _getDisplayedConfidence = () => {
    if (activeTab === 'language' && result.language_confidence_score) {
      return result.language_confidence_score;
    }
    return result.confidence_score;
  };

  return (
    <div className="space-y-6 sm:space-y-8 animate-fade-in">
      {/* Hero Section - Mobile Optimized */}
      <div className="text-center space-y-4 sm:space-y-6">
        <div className="relative">
          <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-success-500 via-brand-600 to-accent-600 rounded-2xl sm:rounded-3xl flex items-center justify-center mx-auto shadow-glow">
            <Sparkles className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
          </div>
        </div>

        <div className="space-y-2 px-4 sm:px-0">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold bg-gradient-to-r from-primary-900 via-brand-700 to-success-700 bg-clip-text text-transparent">
            Übersetzung abgeschlossen
          </h2>
          <p className="text-base sm:text-lg text-primary-600 max-w-3xl mx-auto">
            {result.language_translated_text
              ? 'Ihr medizinisches Dokument wurde vereinfacht und übersetzt'
              : 'Ihr medizinisches Dokument wurde erfolgreich in verständliche Sprache übersetzt'}
          </p>
        </div>
      </div>

      {/* Sprache Card - Mobile Optimized */}
      {result.language_translated_text && result.target_language && (
        <div className="flex justify-center mb-4 sm:mb-6 px-4 sm:px-0">
          <div className="feature-card group w-full sm:max-w-xs">
            <div className="flex items-center space-x-3 sm:space-x-4">
              <div className="feature-icon">
                <Globe className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div className="flex-1">
                <div className="text-xs sm:text-sm font-medium text-primary-600 mb-1">
                  Zielsprache
                </div>
                <div className="font-bold text-primary-900 text-base sm:text-lg">
                  {result.target_language.toUpperCase()}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs für Sprachversionen - Mobile Optimized */}
      {result.language_translated_text && (
        <div className="flex justify-center px-4 sm:px-0">
          <div className="inline-flex bg-neutral-100 rounded-lg sm:rounded-xl p-1 w-full sm:w-auto">
            <button
              onClick={() => setActiveTab('simplified')}
              className={`flex-1 sm:flex-initial px-3 sm:px-6 py-2 sm:py-3 text-xs sm:text-sm font-medium rounded-md sm:rounded-lg transition-all duration-200 ${
                activeTab === 'simplified'
                  ? 'bg-white text-brand-700 shadow-sm'
                  : 'text-neutral-600 hover:text-neutral-800'
              }`}
            >
              📄 Vereinfacht (Deutsch)
            </button>
            <button
              onClick={() => setActiveTab('language')}
              className={`flex-1 sm:flex-initial px-3 sm:px-6 py-2 sm:py-3 text-xs sm:text-sm font-medium rounded-md sm:rounded-lg transition-all duration-200 ${
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

      {/* Main Translation Card - Mobile Optimized */}
      <div className="card-elevated border-brand-200/50 bg-gradient-to-br from-brand-50/30 to-accent-50/30">
        <div className="card-body">
          <div className="mb-6 sm:mb-8">
            {activeTab === 'language' && (
              <div className="flex items-center space-x-3 sm:space-x-4 mb-4">
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-gradient-to-br from-brand-500 via-brand-600 to-accent-600 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-soft flex-shrink-0">
                  <Globe className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 text-white" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-lg sm:text-xl lg:text-2xl font-bold text-primary-900">
                    Übersetzung ({result.target_language?.toUpperCase()})
                  </h3>
                  <p className="text-xs sm:text-sm lg:text-base text-primary-600">
                    Ihr Dokument in {result.target_language}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Translation Content - Mobile Optimized */}
          <div className="relative">
            <div className="glass-card p-4 sm:p-6 md:p-8 lg:p-10">
              <div
                id={
                  activeTab === 'language'
                    ? 'translation-content-language'
                    : 'translation-content-simplified'
                }
                className="medical-text-formatted text-primary-800 leading-relaxed markdown-content"
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  className="prose prose-sm max-w-none"
                  components={{
                    h1: ({ children }) => (
                      <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-4 mt-6 pb-2 border-b border-gray-200">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="text-xl sm:text-2xl font-bold text-gray-800 mb-3 mt-6 pb-1 border-b border-gray-100">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="text-lg sm:text-xl font-semibold text-gray-800 mb-2 mt-4">
                        {children}
                      </h3>
                    ),
                    h4: ({ children }) => (
                      <h4 className="text-base sm:text-lg font-semibold text-gray-700 mb-2 mt-3">
                        {children}
                      </h4>
                    ),
                    h5: ({ children }) => (
                      <h5 className="text-sm sm:text-base font-medium text-gray-700 mb-1 mt-2">
                        {children}
                      </h5>
                    ),
                    h6: ({ children }) => (
                      <h6 className="text-sm font-medium text-gray-600 mb-1 mt-2 uppercase tracking-wide">
                        {children}
                      </h6>
                    ),
                    p: ({ children }) => (
                      <p className="mb-2 text-gray-700 leading-relaxed">{children}</p>
                    ),
                    ul: ({ children }) => (
                      <ul className="list-none pl-0 mb-2 space-y-0">{children}</ul>
                    ),
                    li: ({ children }) => {
                      return (
                        <li className="flex items-start text-gray-800 leading-snug py-0.5">
                          <span className="text-blue-500 mr-2 mt-0.5 flex-shrink-0">•</span>
                          <span>{children}</span>
                        </li>
                      );
                    },
                    strong: ({ children }) => (
                      <strong className="font-semibold text-gray-900">{children}</strong>
                    ),
                    em: ({ children }) => <em className="italic text-gray-600">{children}</em>,
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-4 border-brand-400 pl-4 py-2 my-4 bg-brand-50/50 rounded-r-lg">
                        {children}
                      </blockquote>
                    ),
                    code: ({ children, className }) => {
                      const isInline = !className?.includes('language-');
                      return isInline ? (
                        <code className="bg-primary-100 text-primary-800 px-1.5 py-0.5 rounded text-sm font-mono">
                          {children}
                        </code>
                      ) : (
                        <pre className="bg-primary-100 text-primary-800 p-4 rounded-lg overflow-x-auto mb-4">
                          <code className="font-mono text-sm">{children}</code>
                        </pre>
                      );
                    },
                    hr: () => <hr className="my-6 border-primary-200" />,
                    table: ({ children }) => (
                      <div className="overflow-x-auto mb-4">
                        <table className="min-w-full divide-y divide-primary-200">{children}</table>
                      </div>
                    ),
                    thead: ({ children }) => <thead className="bg-primary-50">{children}</thead>,
                    tbody: ({ children }) => (
                      <tbody className="divide-y divide-primary-100">{children}</tbody>
                    ),
                    tr: ({ children }) => <tr>{children}</tr>,
                    th: ({ children }) => (
                      <th className="px-4 py-2 text-left text-xs font-medium text-primary-700 uppercase tracking-wider">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="px-4 py-2 text-sm text-primary-600 whitespace-pre-line">{children}</td>
                    ),
                  }}
                >
                  {getDisplayedText()}
                </ReactMarkdown>

                {/* PDF Footer with Date - wird nur im Export angezeigt */}
                <div className="mt-8 pt-4 border-t border-primary-200 text-center text-sm text-primary-600">
                  <p>
                    Übersetzung erstellt am:{' '}
                    {new Date().toLocaleDateString('de-DE', {
                      day: '2-digit',
                      month: '2-digit',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                  <p className="text-xs mt-1">HealthLingo - Medizinische Dokumente verstehen</p>
                </div>
              </div>
            </div>

            {/* Decorative elements */}
            <div className="absolute -top-2 -left-2 w-6 h-6 bg-gradient-to-br from-brand-400 to-brand-500 rounded-full opacity-60"></div>
            <div className="absolute -bottom-2 -right-2 w-4 h-4 bg-gradient-to-br from-accent-400 to-accent-500 rounded-full opacity-60"></div>
          </div>

          {/* Processing time indicator with action buttons - Mobile Optimized */}
          <div className="mt-4 sm:mt-6 glass-effect p-3 sm:p-4 rounded-lg sm:rounded-xl">
            <div className="flex flex-col sm:flex-row items-center justify-between space-y-3 sm:space-y-0">
              <div className="flex items-center space-x-2 sm:space-x-3">
                <div className="w-6 h-6 sm:w-8 sm:h-8 rounded-md sm:rounded-lg flex items-center justify-center bg-primary-100">
                  <Clock className="w-3 h-3 sm:w-4 sm:h-4 text-primary-600" />
                </div>
                <div>
                  <div>
                    <span className="text-xs text-primary-500">Verarbeitet in</span>
                    <span className="font-semibold text-primary-700 ml-1 sm:ml-2">
                      {ApiService.formatDuration(result.processing_time_seconds)}
                    </span>
                  </div>
                  <div className="mt-1">
                    <span className="text-xs text-primary-500">Verarbeitungs-ID:</span>
                    <span className="font-mono text-xs text-primary-500 ml-1">{result.processing_id}</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-row space-x-2 sm:space-x-3 w-full sm:w-auto">
                <button
                  onClick={() =>
                    handleCopy(
                      getDisplayedText(),
                      activeTab === 'language' ? 'language' : 'translated'
                    )
                  }
                  className="btn-secondary group flex-1 sm:flex-initial"
                  disabled={copiedText === (activeTab === 'language' ? 'language' : 'translated')}
                >
                  {copiedText === (activeTab === 'language' ? 'language' : 'translated') ? (
                    <>
                      <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 text-success-600 flex-shrink-0" />
                      <span className="text-success-600 hidden sm:inline">Kopiert!</span>
                      <span className="text-success-600 sm:hidden">✓</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3 sm:w-4 sm:h-4 transition-transform duration-200 group-hover:scale-110 flex-shrink-0" />
                      <span className="hidden sm:inline">Kopieren</span>
                      <span className="sm:hidden">Copy</span>
                    </>
                  )}
                </button>

                <button
                  onClick={handleDownload}
                  className="btn-primary group flex-1 sm:flex-initial"
                >
                  <Download className="w-3 h-3 sm:w-4 sm:h-4 transition-transform duration-200 group-hover:scale-110 flex-shrink-0" />
                  <span className="hidden sm:inline">Als PDF</span>
                  <span className="sm:hidden">PDF</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Original Text Section - Only visible for Admin users */}
      {isAdmin && (
        <div className="card-elevated">
          <div className="card-body">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 sm:mb-6 space-y-3 sm:space-y-0">
              <div className="flex items-center space-x-2 sm:space-x-3">
                <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg sm:rounded-xl flex items-center justify-center">
                  <FileText className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-primary-900">Originaltext</h3>
              </div>

              <div className="flex space-x-2 sm:space-x-3">
                <button
                  onClick={() => setShowOriginal(!showOriginal)}
                  className="btn-secondary group"
                >
                  {showOriginal ? (
                    <>
                      <EyeOff className="w-3 h-3 sm:w-4 sm:h-4 transition-transform duration-200 group-hover:scale-110 flex-shrink-0" />
                      <span className="hidden sm:inline">Ausblenden</span>
                      <span className="sm:hidden">Hide</span>
                    </>
                  ) : (
                    <>
                      <Eye className="w-3 h-3 sm:w-4 sm:h-4 transition-transform duration-200 group-hover:scale-110 flex-shrink-0" />
                      <span className="hidden sm:inline">Anzeigen</span>
                      <span className="sm:hidden">Show</span>
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
                        <CheckCircle className="w-3 h-3 sm:w-4 sm:h-4 text-success-600 flex-shrink-0" />
                        <span className="text-success-600 hidden sm:inline">Kopiert!</span>
                        <span className="text-success-600 sm:hidden">✓</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3 sm:w-4 sm:h-4 transition-transform duration-200 group-hover:scale-110 flex-shrink-0" />
                        <span className="hidden sm:inline">Kopieren</span>
                        <span className="sm:hidden">Copy</span>
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {showOriginal && (
              <div className="animate-slide-down">
                <div className="text-result bg-gradient-to-br from-neutral-50 to-primary-50/30">
                  {/* Raw text display - no markdown formatting, preserves whitespace */}
                  <pre className="whitespace-pre-wrap font-mono text-sm text-primary-800 leading-relaxed overflow-x-auto">
                    {result.original_text}
                  </pre>
                </div>
              </div>
            )}

            {!showOriginal && (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Eye className="w-8 h-8 text-primary-500" />
                </div>
                <p className="text-primary-600">
                  Klicken Sie auf &quot;Anzeigen&quot;, um den Originaltext zu sehen
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Feedback Widget (Issue #47) */}
      <FeedbackWidget
        processingId={result.processing_id}
        onFeedbackSubmitted={() => setFeedbackSubmitted(true)}
      />

      {/* Action Button - Centered */}
      <div className="flex justify-center pt-6">
        <button onClick={handleNewTranslation} className="btn-primary group">
          <RefreshCw className="w-5 h-5 transition-transform duration-200 group-hover:rotate-180 flex-shrink-0" />
          <span>Neues Dokument übersetzen</span>
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
              Diese Übersetzung wurde automatisch erstellt und dient nur zur Orientierung. Sie
              ersetzt nicht die professionelle medizinische Beratung, Diagnose oder Behandlung.
              Wenden Sie sich bei Fragen immer an Ihren Arzt oder andere qualifizierte
              Gesundheitsdienstleister.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TranslationResult;
