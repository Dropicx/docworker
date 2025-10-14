/**
 * Document Class Manager Component
 *
 * Allows users to configure dynamic document classification types:
 * - View all document classes (system and custom)
 * - Create new custom document classes
 * - Edit existing classes
 * - Delete custom classes (system classes protected)
 * - Configure classification indicators
 */

import React, { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  Edit2,
  Trash2,
  AlertCircle,
  CheckCircle,
  Loader2,
  Shield,
  List,
  Star
} from 'lucide-react';
import { pipelineApi } from '../../services/pipelineApi';
import {
  DocumentClass,
  DocumentClassRequest,
  DocumentClassStatistics
} from '../../types/pipeline';

const DocumentClassManager: React.FC = () => {
  // State
  const [classes, setClasses] = useState<DocumentClass[]>([]);
  const [statistics, setStatistics] = useState<DocumentClassStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');

  // Editor state
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingClass, setEditingClass] = useState<DocumentClass | null>(null);
  const [formData, setFormData] = useState<DocumentClassRequest>({
    class_key: '',
    display_name: '',
    description: '',
    icon: '',
    examples: [],
    strong_indicators: [],
    weak_indicators: [],
    is_enabled: true
  });

  // Input state for arrays
  const [exampleInput, setExampleInput] = useState('');
  const [strongIndicatorInput, setStrongIndicatorInput] = useState('');
  const [weakIndicatorInput, setWeakIndicatorInput] = useState('');

  // Load data on mount
  useEffect(() => {
    loadClasses();
    loadStatistics();
  }, []);

  // ==================== DATA LOADING ====================

  const loadClasses = async () => {
    setLoading(true);
    setError('');
    try {
      const classesData = await pipelineApi.getAllDocumentClasses(false);
      setClasses(classesData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const stats = await pipelineApi.getDocumentClassStatistics();
      setStatistics(stats);
    } catch (err) {
      console.error('Failed to load statistics:', err);
    }
  };

  // ==================== CRUD OPERATIONS ====================

  const handleCreate = () => {
    setEditingClass(null);
    setFormData({
      class_key: '',
      display_name: '',
      description: '',
      icon: '📄',
      examples: [],
      strong_indicators: [],
      weak_indicators: [],
      is_enabled: true
    });
    setExampleInput('');
    setStrongIndicatorInput('');
    setWeakIndicatorInput('');
    setIsEditorOpen(true);
  };

  const handleEdit = (docClass: DocumentClass) => {
    setEditingClass(docClass);
    setFormData({
      class_key: docClass.class_key,
      display_name: docClass.display_name,
      description: docClass.description || '',
      icon: docClass.icon || '📄',
      examples: docClass.examples || [],
      strong_indicators: docClass.strong_indicators || [],
      weak_indicators: docClass.weak_indicators || [],
      is_enabled: docClass.is_enabled
    });
    setExampleInput('');
    setStrongIndicatorInput('');
    setWeakIndicatorInput('');
    setIsEditorOpen(true);
  };

  const handleSave = async () => {
    setError('');
    setSuccess('');

    // Validation
    if (!formData.class_key.trim()) {
      setError('Class Key ist erforderlich');
      return;
    }
    if (!formData.display_name.trim()) {
      setError('Display Name ist erforderlich');
      return;
    }

    setLoading(true);

    try {
      if (editingClass) {
        // Update existing class
        await pipelineApi.updateDocumentClass(editingClass.id, formData);
        setSuccess(`Dokumentenklasse "${formData.display_name}" erfolgreich aktualisiert!`);
      } else {
        // Create new class
        await pipelineApi.createDocumentClass(formData);
        setSuccess(`Dokumentenklasse "${formData.display_name}" erfolgreich erstellt!`);
      }

      setIsEditorOpen(false);
      await loadClasses();
      await loadStatistics();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (docClass: DocumentClass) => {
    if (docClass.is_system_class) {
      setError('Systemklassen können nicht gelöscht werden');
      return;
    }

    if (!confirm(`Möchten Sie die Dokumentenklasse "${docClass.display_name}" wirklich löschen?`)) {
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      await pipelineApi.deleteDocumentClass(docClass.id);
      setSuccess(`Dokumentenklasse "${docClass.display_name}" erfolgreich gelöscht!`);
      await loadClasses();
      await loadStatistics();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // ==================== ARRAY FIELD HANDLERS ====================

  const handleAddExample = () => {
    if (exampleInput.trim()) {
      setFormData({
        ...formData,
        examples: [...(formData.examples || []), exampleInput.trim()]
      });
      setExampleInput('');
    }
  };

  const handleRemoveExample = (index: number) => {
    setFormData({
      ...formData,
      examples: formData.examples?.filter((_, i) => i !== index) || []
    });
  };

  const handleAddStrongIndicator = () => {
    if (strongIndicatorInput.trim()) {
      setFormData({
        ...formData,
        strong_indicators: [...(formData.strong_indicators || []), strongIndicatorInput.trim()]
      });
      setStrongIndicatorInput('');
    }
  };

  const handleRemoveStrongIndicator = (index: number) => {
    setFormData({
      ...formData,
      strong_indicators: formData.strong_indicators?.filter((_, i) => i !== index) || []
    });
  };

  const handleAddWeakIndicator = () => {
    if (weakIndicatorInput.trim()) {
      setFormData({
        ...formData,
        weak_indicators: [...(formData.weak_indicators || []), weakIndicatorInput.trim()]
      });
      setWeakIndicatorInput('');
    }
  };

  const handleRemoveWeakIndicator = (index: number) => {
    setFormData({
      ...formData,
      weak_indicators: formData.weak_indicators?.filter((_, i) => i !== index) || []
    });
  };

  // ==================== RENDER ====================

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      {statistics && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-blue-600">Gesamt</p>
                <p className="text-2xl font-bold text-blue-900">{statistics.total_classes}</p>
              </div>
              <FileText className="w-8 h-8 text-blue-500" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl border border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-green-600">Aktiv</p>
                <p className="text-2xl font-bold text-green-900">{statistics.enabled_classes}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl border border-purple-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-purple-600">System</p>
                <p className="text-2xl font-bold text-purple-900">{statistics.system_classes}</p>
              </div>
              <Shield className="w-8 h-8 text-purple-500" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-xl border border-orange-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-orange-600">Benutzerdefiniert</p>
                <p className="text-2xl font-bold text-orange-900">{statistics.custom_classes}</p>
              </div>
              <Star className="w-8 h-8 text-orange-500" />
            </div>
          </div>
        </div>
      )}

      {/* Header with Create Button */}
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-primary-900">Dokumentenklassen</h3>
        <button
          onClick={handleCreate}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-brand-600 to-brand-700 text-white rounded-lg hover:from-brand-700 hover:to-brand-800 transition-all shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>Neue Klasse</span>
        </button>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {success && (
        <div className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
          <p className="text-sm text-green-700">{success}</p>
        </div>
      )}

      {/* Document Classes List */}
      {loading && !classes.length ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {classes.map((docClass) => (
            <div
              key={docClass.id}
              className={`p-4 rounded-xl border-2 transition-all ${
                docClass.is_enabled
                  ? 'bg-white border-primary-200 hover:border-brand-300'
                  : 'bg-gray-50 border-gray-200 opacity-60'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  {/* Icon */}
                  <div className="text-4xl">{docClass.icon || '📄'}</div>

                  {/* Info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="text-lg font-semibold text-primary-900">
                        {docClass.display_name}
                      </h4>
                      <span className="px-2 py-0.5 text-xs font-mono bg-primary-100 text-primary-700 rounded">
                        {docClass.class_key}
                      </span>
                      {docClass.is_system_class && (
                        <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded flex items-center space-x-1">
                          <Shield className="w-3 h-3" />
                          <span>System</span>
                        </span>
                      )}
                      {!docClass.is_enabled && (
                        <span className="px-2 py-0.5 text-xs bg-gray-200 text-gray-600 rounded">
                          Deaktiviert
                        </span>
                      )}
                    </div>

                    {docClass.description && (
                      <p className="text-sm text-primary-600 mb-3">{docClass.description}</p>
                    )}

                    {/* Indicators */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      {docClass.strong_indicators && docClass.strong_indicators.length > 0 && (
                        <div>
                          <p className="font-medium text-primary-700 mb-1 flex items-center space-x-1">
                            <Star className="w-3 h-3" />
                            <span>Starke Indikatoren:</span>
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {docClass.strong_indicators.slice(0, 5).map((indicator, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs"
                              >
                                {indicator}
                              </span>
                            ))}
                            {docClass.strong_indicators.length > 5 && (
                              <span className="px-2 py-0.5 bg-green-50 text-green-600 rounded text-xs">
                                +{docClass.strong_indicators.length - 5} mehr
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {docClass.examples && docClass.examples.length > 0 && (
                        <div>
                          <p className="font-medium text-primary-700 mb-1 flex items-center space-x-1">
                            <List className="w-3 h-3" />
                            <span>Beispiele:</span>
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {docClass.examples.slice(0, 3).map((example, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs"
                              >
                                {example}
                              </span>
                            ))}
                            {docClass.examples.length > 3 && (
                              <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">
                                +{docClass.examples.length - 3} mehr
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleEdit(docClass)}
                    className="p-2 hover:bg-brand-50 text-brand-600 rounded-lg transition-colors"
                    title="Bearbeiten"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>

                  {!docClass.is_system_class && (
                    <button
                      onClick={() => handleDelete(docClass)}
                      disabled={loading}
                      className="p-2 hover:bg-red-50 text-red-600 rounded-lg transition-colors disabled:opacity-50"
                      title="Löschen"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Editor Modal */}
      {isEditorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="relative w-full max-w-3xl max-h-[90vh] bg-white rounded-2xl shadow-2xl border border-primary-200 flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="p-6 border-b border-primary-200 bg-gradient-to-r from-brand-50 to-accent-50">
              <h3 className="text-xl font-bold text-primary-900">
                {editingClass ? 'Dokumentenklasse bearbeiten' : 'Neue Dokumentenklasse'}
              </h3>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary-700 mb-2">
                    Class Key * <span className="text-xs text-gray-500">(z.B. &quot;ARZTBRIEF&quot;)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.class_key}
                    onChange={(e) => setFormData({ ...formData, class_key: e.target.value.toUpperCase() })}
                    disabled={editingClass?.is_system_class}
                    className="w-full px-3 py-2 border border-primary-300 rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:bg-gray-100"
                    placeholder="BEISPIEL"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-primary-700 mb-2">
                    Display Name *
                  </label>
                  <input
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                    className="w-full px-3 py-2 border border-primary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    placeholder="Beispiel Dokument"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-primary-700 mb-2">
                    Icon (Emoji)
                  </label>
                  <input
                    type="text"
                    value={formData.icon ?? ''}
                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                    className="w-full px-3 py-2 border border-primary-300 rounded-lg text-2xl text-center focus:outline-none focus:ring-2 focus:ring-brand-500"
                    placeholder="📄"
                    maxLength={2}
                  />
                </div>

                <div className="flex items-end">
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={formData.is_enabled}
                      onChange={(e) => setFormData({ ...formData, is_enabled: e.target.checked })}
                      className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                    />
                    <span className="text-sm font-medium text-primary-700">Aktiv</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-primary-700 mb-2">
                  Beschreibung
                </label>
                <textarea
                  value={formData.description ?? ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-primary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                  rows={3}
                  placeholder="Beschreibung der Dokumentenklasse..."
                />
              </div>

              {/* Examples */}
              <div>
                <label className="block text-sm font-medium text-primary-700 mb-2">
                  Beispiele
                </label>
                <div className="flex space-x-2 mb-2">
                  <input
                    type="text"
                    value={exampleInput}
                    onChange={(e) => setExampleInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddExample()}
                    className="flex-1 px-3 py-2 border border-primary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    placeholder="Beispiel hinzufügen..."
                  />
                  <button
                    onClick={handleAddExample}
                    className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.examples?.map((example, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg text-sm flex items-center space-x-2"
                    >
                      <span>{example}</span>
                      <button
                        onClick={() => handleRemoveExample(idx)}
                        className="text-blue-500 hover:text-blue-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Strong Indicators */}
              <div>
                <label className="block text-sm font-medium text-primary-700 mb-2">
                  Starke Indikatoren (Schlüsselwörter)
                </label>
                <div className="flex space-x-2 mb-2">
                  <input
                    type="text"
                    value={strongIndicatorInput}
                    onChange={(e) => setStrongIndicatorInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddStrongIndicator()}
                    className="flex-1 px-3 py-2 border border-primary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    placeholder="Indikator hinzufügen..."
                  />
                  <button
                    onClick={handleAddStrongIndicator}
                    className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.strong_indicators?.map((indicator, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-sm flex items-center space-x-2"
                    >
                      <span>{indicator}</span>
                      <button
                        onClick={() => handleRemoveStrongIndicator(idx)}
                        className="text-green-500 hover:text-green-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>

              {/* Weak Indicators */}
              <div>
                <label className="block text-sm font-medium text-primary-700 mb-2">
                  Schwache Indikatoren (optionale Hinweise)
                </label>
                <div className="flex space-x-2 mb-2">
                  <input
                    type="text"
                    value={weakIndicatorInput}
                    onChange={(e) => setWeakIndicatorInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAddWeakIndicator()}
                    className="flex-1 px-3 py-2 border border-primary-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                    placeholder="Indikator hinzufügen..."
                  />
                  <button
                    onClick={handleAddWeakIndicator}
                    className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {formData.weak_indicators?.map((indicator, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-lg text-sm flex items-center space-x-2"
                    >
                      <span>{indicator}</span>
                      <button
                        onClick={() => handleRemoveWeakIndicator(idx)}
                        className="text-yellow-500 hover:text-yellow-700"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-primary-200 bg-gray-50 flex items-center justify-end space-x-3">
              <button
                onClick={() => setIsEditorOpen(false)}
                disabled={loading}
                className="px-4 py-2 border border-primary-300 text-primary-700 rounded-lg hover:bg-primary-50 transition-colors disabled:opacity-50"
              >
                Abbrechen
              </button>
              <button
                onClick={handleSave}
                disabled={loading}
                className="flex items-center space-x-2 px-6 py-2 bg-gradient-to-r from-brand-600 to-brand-700 text-white rounded-lg hover:from-brand-700 hover:to-brand-800 transition-all shadow-sm disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Speichere...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    <span>Speichern</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentClassManager;
