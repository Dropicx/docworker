import React, { useState } from 'react';
import { Copy, Download, Eye, EyeOff, CheckCircle, FileText, Clock, Star } from 'lucide-react';
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
  const [copiedText, setCopiedText] = useState<'original' | 'translated' | null>(null);

  const handleCopy = async (text: string, type: 'original' | 'translated') => {
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
Verarbeitungszeit: ${ApiService.formatDuration(result.processing_time_seconds)}
Zeitstempel: ${new Date(result.timestamp).toLocaleString('de-DE')}

ÜBERSETZUNG IN EINFACHER SPRACHE:
${result.translated_text}

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
    if (score >= 0.8) return 'text-success-600 bg-success-100';
    if (score >= 0.6) return 'text-warning-600 bg-warning-100';
    return 'text-error-600 bg-error-100';
  };

  const getConfidenceText = (score: number) => {
    if (score >= 0.8) return 'Hoch';
    if (score >= 0.6) return 'Mittel';
    return 'Niedrig';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header mit Metadaten */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">
              Übersetzung abgeschlossen
            </h2>
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-6 h-6 text-success-600" />
              <span className="text-success-600 font-medium">Erfolgreich</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Dokumenttyp */}
            <div className="flex items-center p-3 bg-gray-50 rounded-lg">
              <FileText className="w-5 h-5 text-gray-600 mr-3" />
              <div>
                <div className="text-sm text-gray-600">Dokumenttyp</div>
                <div className="font-medium text-gray-900 capitalize">
                  {result.document_type_detected}
                </div>
              </div>
            </div>

            {/* Vertrauensgrad */}
            <div className="flex items-center p-3 bg-gray-50 rounded-lg">
              <Star className="w-5 h-5 text-gray-600 mr-3" />
              <div>
                <div className="text-sm text-gray-600">Vertrauensgrad</div>
                <div className={`font-medium px-2 py-1 rounded-full text-xs ${getConfidenceColor(result.confidence_score)}`}>
                  {getConfidenceText(result.confidence_score)} ({(result.confidence_score * 100).toFixed(1)}%)
                </div>
              </div>
            </div>

            {/* Verarbeitungszeit */}
            <div className="flex items-center p-3 bg-gray-50 rounded-lg">
              <Clock className="w-5 h-5 text-gray-600 mr-3" />
              <div>
                <div className="text-sm text-gray-600">Verarbeitungszeit</div>
                <div className="font-medium text-gray-900">
                  {ApiService.formatDuration(result.processing_time_seconds)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Übersetzter Text */}
      <div className="card shadow-xl">
        <div className="card-body">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-success-500 to-medical-500 rounded-lg flex items-center justify-center">
                <span className="text-white text-lg">📄</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">
                Verständliche Zusammenfassung
              </h3>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => handleCopy(result.translated_text, 'translated')}
                className="btn-secondary flex items-center space-x-2 text-sm hover:scale-105 transition-transform"
              >
                {copiedText === 'translated' ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-success-600" />
                    <span className="text-success-600">Kopiert!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span>Kopieren</span>
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="prose max-w-none">
            <div className="bg-gradient-to-br from-success-50 via-medical-50 to-blue-50 border-l-4 border-success-500 p-8 rounded-xl shadow-inner">
              <div className="medical-text-formatted text-gray-800 leading-relaxed whitespace-pre-wrap">
                {result.translated_text}
              </div>
            </div>
          </div>

          {/* Quality indicator */}
          <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
            <div className="flex items-center space-x-2">
              <span className="flex items-center">
                <Star className="w-4 h-4 text-yellow-500 mr-1" />
                Qualität: <span className={`ml-1 font-medium ${getConfidenceColor(result.confidence_score)}`}>
                  {getConfidenceText(result.confidence_score)}
                </span>
              </span>
            </div>
            <span className="text-xs text-gray-500">
              Verarbeitungszeit: {ApiService.formatDuration(result.processing_time_seconds)}
            </span>
          </div>
        </div>
      </div>

      {/* Originaltext (optional) */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Originaltext
            </h3>
            <div className="flex space-x-2">
              <button
                onClick={() => setShowOriginal(!showOriginal)}
                className="btn-secondary flex items-center space-x-2 text-sm"
              >
                {showOriginal ? (
                  <>
                    <EyeOff className="w-4 h-4" />
                    <span>Ausblenden</span>
                  </>
                ) : (
                  <>
                    <Eye className="w-4 h-4" />
                    <span>Anzeigen</span>
                  </>
                )}
              </button>
              
              {showOriginal && (
                <button
                  onClick={() => handleCopy(result.original_text, 'original')}
                  className="btn-secondary flex items-center space-x-2 text-sm"
                >
                  {copiedText === 'original' ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span>Kopiert!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span>Kopieren</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          {showOriginal && (
            <div className="text-result scrollbar-thin animate-slide-up">
              {result.original_text}
            </div>
          )}
        </div>
      </div>

      {/* Aktionen */}
      <div className="card">
        <div className="card-body">
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={handleDownload}
              className="btn-primary flex items-center justify-center space-x-2"
            >
              <Download className="w-5 h-5" />
              <span>Als Textdatei herunterladen</span>
            </button>
            
            <button
              onClick={onNewTranslation}
              className="btn-secondary flex items-center justify-center space-x-2"
            >
              <FileText className="w-5 h-5" />
              <span>Neues Dokument übersetzen</span>
            </button>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="card border-warning-200 bg-warning-50">
        <div className="card-body">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg className="w-5 h-5 text-warning-600 mt-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h4 className="text-sm font-medium text-warning-800 mb-1">
                Wichtiger Hinweis
              </h4>
              <p className="text-sm text-warning-700">
                Diese Übersetzung wurde automatisch erstellt und dient nur der Orientierung. 
                Sie ersetzt nicht die professionelle medizinische Beratung, Diagnose oder Behandlung. 
                Wenden Sie sich bei Fragen immer an Ihren Arzt oder medizinisches Fachpersonal.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Technische Details */}
      <div className="text-center">
        <div className="text-xs text-gray-500">
          Verarbeitungs-ID: {result.processing_id} | 
          Erstellt am: {new Date(result.timestamp).toLocaleString('de-DE')}
        </div>
      </div>
    </div>
  );
};

export default TranslationResult; 