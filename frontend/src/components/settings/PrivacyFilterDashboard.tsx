import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Brain,
  Database,
  Pill,
  FileText,
  Play,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import { privacyFilterApi } from '../../services/privacyFilterApi';
import {
  PrivacyMetrics,
  LiveTestResult,
  PIIType,
  PrivacyHealth,
} from '../../types/privacy';

const PrivacyFilterDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<PrivacyMetrics | null>(null);
  const [health, setHealth] = useState<PrivacyHealth | null>(null);
  const [piiTypes, setPiiTypes] = useState<PIIType[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  // Live test state
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState<LiveTestResult | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [metricsData, healthData, piiTypesData] = await Promise.all([
        privacyFilterApi.getMetrics(),
        privacyFilterApi.getHealth(),
        privacyFilterApi.getPIITypes(),
      ]);
      setMetrics(metricsData);
      setHealth(healthData);
      setPiiTypes(piiTypesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    if (autoRefresh) {
      const interval = setInterval(fetchData, 10000); // Refresh every 10 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchData]);

  const handleRefresh = () => {
    fetchData();
  };

  const handleTest = async () => {
    if (!testText.trim()) return;

    setIsTesting(true);
    setTestError(null);
    setTestResult(null);

    try {
      const result = await privacyFilterApi.testText(testText);
      setTestResult(result);
    } catch (err) {
      setTestError(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setIsTesting(false);
    }
  };

  if (isLoading && !metrics) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center space-y-4">
          <RefreshCw className="w-12 h-12 text-brand-600 animate-spin mx-auto" />
          <p className="text-primary-600">Lade Datenschutz-Filter Daten...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-primary-900">Datenschutz-Filter</h3>
          <button
            onClick={handleRefresh}
            className="flex items-center space-x-2 px-4 py-2 text-sm bg-brand-100 hover:bg-brand-200 text-brand-700 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Aktualisieren</span>
          </button>
        </div>

        <div className="bg-error-50 border border-error-200 rounded-lg p-6">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-6 h-6 text-error-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h4 className="text-lg font-semibold text-error-900">
                Fehler beim Laden
              </h4>
              <p className="text-sm text-error-700">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-primary-900">Datenschutz-Filter</h3>
            <p className="text-sm text-primary-600">GDPR-konforme PII-Erkennung und -Entfernung</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Health Status Badge */}
          <div
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-sm font-medium ${
              health?.status === 'healthy'
                ? 'bg-success-100 text-success-700'
                : 'bg-error-100 text-error-700'
            }`}
          >
            {health?.status === 'healthy' ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <AlertCircle className="w-4 h-4" />
            )}
            <span>{health?.status === 'healthy' ? 'Aktiv' : 'Fehler'}</span>
          </div>

          <label className="flex items-center space-x-2 text-sm text-primary-700">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-primary-300 text-brand-600 focus:ring-brand-500"
            />
            <span>Auto-Refresh (10s)</span>
          </label>
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 text-sm bg-brand-100 hover:bg-brand-200 text-brand-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Aktualisieren</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* NER Status */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Brain className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-primary-900">NER Engine</h4>
            </div>
            {metrics?.filter_capabilities.has_ner ? (
              <CheckCircle className="w-5 h-5 text-success-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-warning-600" />
            )}
          </div>
          <div className="space-y-2">
            <span
              className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                metrics?.filter_capabilities.has_ner
                  ? 'bg-success-100 text-success-700'
                  : 'bg-warning-100 text-warning-700'
              }`}
            >
              {metrics?.filter_capabilities.has_ner ? 'Aktiv' : 'Deaktiviert'}
            </span>
            <p className="text-xs text-primary-500">
              Modell: {metrics?.filter_capabilities.spacy_model || 'none'}
            </p>
          </div>
        </div>

        {/* PII Types */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="w-5 h-5 text-primary-600" />
            <h4 className="font-semibold text-primary-900">PII-Typen</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {metrics?.detection_stats.pii_types_count || 0}
            </span>
            <span className="text-sm text-primary-600">erkannte Typen</span>
          </div>
        </div>

        {/* Medical Terms */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Database className="w-5 h-5 text-primary-600" />
            <h4 className="font-semibold text-primary-900">Medizinische Begriffe</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {metrics?.detection_stats.medical_terms_count || 0}
            </span>
            <span className="text-sm text-primary-600">geschützt</span>
          </div>
        </div>

        {/* Drug Database */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Pill className="w-5 h-5 text-primary-600" />
            <h4 className="font-semibold text-primary-900">Medikamente</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {metrics?.detection_stats.drug_database_count || 0}
            </span>
            <span className="text-sm text-primary-600">in Datenbank</span>
          </div>
        </div>
      </div>

      {/* Additional Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-primary-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-primary-600">Abkürzungen</span>
            <span className="font-semibold text-primary-900">
              {metrics?.detection_stats.abbreviations_count || 0}
            </span>
          </div>
        </div>
        <div className="bg-white border border-primary-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-primary-600">Eponyme</span>
            <span className="font-semibold text-primary-900">
              {metrics?.detection_stats.eponyms_count || 0}
            </span>
          </div>
        </div>
        <div className="bg-white border border-primary-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-primary-600">LOINC-Codes</span>
            <span className="font-semibold text-primary-900">
              {metrics?.detection_stats.loinc_codes_count || 0}
            </span>
          </div>
        </div>
      </div>

      {/* PII Types Table */}
      <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-primary-200">
          <h4 className="font-semibold text-primary-900">Erkannte PII-Typen</h4>
          <p className="text-sm text-primary-600">
            Liste aller personenbezogenen Daten, die erkannt und entfernt werden
          </p>
        </div>
        <div className="overflow-x-auto max-h-64 overflow-y-auto">
          <table className="min-w-full divide-y divide-primary-200">
            <thead className="bg-primary-50 sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  Typ
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  Beschreibung
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  Ersetzung
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary-100">
              {piiTypes.map((piiType) => (
                <tr key={piiType.type} className="hover:bg-primary-50">
                  <td className="px-4 py-2 text-sm font-mono text-primary-900">
                    {piiType.type}
                  </td>
                  <td className="px-4 py-2 text-sm text-primary-600">
                    {piiType.description}
                  </td>
                  <td className="px-4 py-2 text-xs font-mono text-primary-500 truncate max-w-xs">
                    {piiType.marker}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live Test Section */}
      <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-primary-200">
          <div className="flex items-center space-x-2">
            <Play className="w-5 h-5 text-primary-600" />
            <div>
              <h4 className="font-semibold text-primary-900">Live-Test</h4>
              <p className="text-sm text-primary-600">
                Testen Sie den Filter mit eigenem Text (Daten werden nicht gespeichert)
              </p>
            </div>
          </div>
        </div>
        <div className="p-4 space-y-4">
          <textarea
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            placeholder="Patient: Müller, Hans&#10;Geb.: 15.05.1965&#10;Tel: +49 89 12345678&#10;Diagnose: Diabetes mellitus Typ 2 (E11.9)"
            className="w-full h-32 px-3 py-2 border border-primary-300 rounded-lg text-sm font-mono resize-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            maxLength={50000}
          />
          <div className="flex items-center justify-between">
            <span className="text-xs text-primary-500">
              {testText.length} / 50.000 Zeichen
            </span>
            <button
              onClick={handleTest}
              disabled={isTesting || !testText.trim()}
              className="flex items-center space-x-2 px-6 py-2 bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isTesting ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>{isTesting ? 'Verarbeite...' : 'Filter testen'}</span>
            </button>
          </div>

          {/* Test Error */}
          {testError && (
            <div className="p-3 bg-error-50 border border-error-200 rounded-lg">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-error-600" />
                <span className="text-sm text-error-700">{testError}</span>
              </div>
            </div>
          )}

          {/* Test Results */}
          {testResult && (
            <div className="p-4 bg-primary-50 border border-primary-200 rounded-lg space-y-4">
              <h5 className="font-semibold text-primary-900">Ergebnis</h5>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-white p-3 rounded border border-primary-200">
                  <div className="flex items-center space-x-2 text-primary-600 mb-1">
                    <Clock className="w-4 h-4" />
                    <span className="text-xs">Verarbeitungszeit</span>
                  </div>
                  <span
                    className={`text-lg font-bold ${
                      testResult.passes_performance_target
                        ? 'text-success-600'
                        : 'text-warning-600'
                    }`}
                  >
                    {testResult.processing_time_ms.toFixed(1)}ms
                  </span>
                </div>

                <div className="bg-white p-3 rounded border border-primary-200">
                  <div className="flex items-center space-x-2 text-primary-600 mb-1">
                    <Shield className="w-4 h-4" />
                    <span className="text-xs">PII gefunden</span>
                  </div>
                  <span className="text-lg font-bold text-primary-900">
                    {testResult.entities_detected}
                  </span>
                </div>

                <div className="bg-white p-3 rounded border border-primary-200">
                  <div className="flex items-center space-x-2 text-primary-600 mb-1">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-xs">Qualitätsscore</span>
                  </div>
                  <span
                    className={`text-lg font-bold ${
                      testResult.quality_score >= 80
                        ? 'text-success-600'
                        : testResult.quality_score >= 50
                        ? 'text-warning-600'
                        : 'text-error-600'
                    }`}
                  >
                    {testResult.quality_score.toFixed(0)}%
                  </span>
                </div>

                <div className="bg-white p-3 rounded border border-primary-200">
                  <div className="flex items-center space-x-2 text-primary-600 mb-1">
                    <FileText className="w-4 h-4" />
                    <span className="text-xs">Textlänge</span>
                  </div>
                  <span className="text-lg font-bold text-primary-900">
                    {testResult.input_length} → {testResult.output_length}
                  </span>
                </div>
              </div>

              {/* Review Warning */}
              {testResult.review_recommended && (
                <div className="flex items-center space-x-2 p-3 bg-warning-50 border border-warning-200 rounded">
                  <AlertTriangle className="w-5 h-5 text-warning-600" />
                  <span className="text-sm text-warning-700">
                    Manuelle Überprüfung empfohlen
                  </span>
                </div>
              )}

              {/* PII Types Detected */}
              {testResult.pii_types_detected.length > 0 && (
                <div>
                  <h6 className="text-sm font-semibold text-primary-700 mb-2">
                    Erkannte PII-Typen:
                  </h6>
                  <div className="flex flex-wrap gap-2">
                    {testResult.pii_types_detected.map((type) => (
                      <span
                        key={type}
                        className="px-2 py-1 bg-brand-100 text-brand-700 text-xs font-mono rounded"
                      >
                        {type}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer Info */}
      <div className="text-xs text-primary-500 text-center">
        Filter-Version: {metrics?.filter_capabilities.removal_method} | Performance-Ziel:{' '}
        {metrics?.performance_target_ms}ms | Letzte Aktualisierung:{' '}
        {metrics?.timestamp ? new Date(metrics.timestamp).toLocaleString('de-DE') : '-'}
      </div>
    </div>
  );
};

export default PrivacyFilterDashboard;
