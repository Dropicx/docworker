/**
 * AI Model Manager Component
 *
 * Allows admins to view and edit AI model pricing information:
 * - View all configured models with details
 * - Edit input/output costs per 1 million tokens
 * - Dynamic handling of any number of models
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Brain,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Loader2,
  Save,
  X,
  Eye,
  EyeOff,
  Cpu,
  DollarSign,
} from 'lucide-react';
import { pipelineApi } from '../../services/pipelineApi';
import { AIModel } from '../../types/pipeline';
import { useAuth } from '../../contexts/AuthContext';

interface EditingModel {
  id: number;
  price_input_per_1m_tokens: number | null;
  price_output_per_1m_tokens: number | null;
}

const AIModelManager: React.FC = () => {
  const { tokens } = useAuth();
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingModel, setEditingModel] = useState<EditingModel | null>(null);
  const [savingModelId, setSavingModelId] = useState<number | null>(null);

  // Sync token with pipeline API
  useEffect(() => {
    if (tokens?.access_token) {
      pipelineApi.updateToken(tokens.access_token);
    }
  }, [tokens]);

  // Load models on mount
  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const modelsData = await pipelineApi.getAvailableModels(false);
      setModels(modelsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Modelle');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleEdit = (model: AIModel) => {
    setEditingModel({
      id: model.id,
      price_input_per_1m_tokens: model.price_input_per_1m_tokens,
      price_output_per_1m_tokens: model.price_output_per_1m_tokens,
    });
  };

  const handleCancel = () => {
    setEditingModel(null);
  };

  const handleSave = async (modelId: number) => {
    if (!editingModel || editingModel.id !== modelId) {
      return;
    }

    setError(null);
    setSuccess(null);
    setSavingModelId(modelId);

    try {
      const updateData: {
        price_input_per_1m_tokens: number | null;
        price_output_per_1m_tokens: number | null;
      } = {
        price_input_per_1m_tokens: editingModel.price_input_per_1m_tokens,
        price_output_per_1m_tokens: editingModel.price_output_per_1m_tokens,
      };

      const updatedModel = await pipelineApi.updateModel(modelId, updateData);

      // Update the model in the list
      setModels(prevModels =>
        prevModels.map(m => (m.id === modelId ? updatedModel : m))
      );

      setSuccess(`Preise für "${updatedModel.display_name}" erfolgreich aktualisiert!`);
      setEditingModel(null);

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern der Preise');
    } finally {
      setSavingModelId(null);
    }
  };

  const formatPrice = (price: number | null): string => {
    if (price === null || price === undefined) {
      return 'N/A';
    }
    return `$${price.toFixed(4)}`;
  };

  const formatNumber = (num: number | null): string => {
    if (num === null || num === undefined) {
      return 'N/A';
    }
    return num.toLocaleString('de-DE');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          <span className="text-sm text-neutral-600">Lade Modelle...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Brain className="w-6 h-6 text-brand-600" />
          <h2 className="text-xl font-bold text-neutral-900">AI Modelle</h2>
        </div>
        <button
          onClick={loadModels}
          className="flex items-center space-x-2 px-4 py-2 text-neutral-600 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
          title="Aktualisieren"
        >
          <RefreshCw className="w-5 h-5" />
          <span className="hidden sm:inline">Aktualisieren</span>
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center space-x-2 p-4 bg-error-50 border border-error-200 rounded-lg text-error-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="flex items-center space-x-2 p-4 bg-success-50 border border-success-200 rounded-lg text-success-700">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Models Grid */}
      {models.length === 0 ? (
        <div className="text-center py-12 text-neutral-500">
          <Brain className="w-12 h-12 mx-auto mb-4 text-neutral-300" />
          <p>Keine Modelle gefunden</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {models.map(model => {
            const isEditing = editingModel?.id === model.id;
            const isSaving = savingModelId === model.id;

            return (
              <div
                key={model.id}
                className="bg-white border border-neutral-200 rounded-lg p-6 hover:shadow-md transition-shadow"
              >
                {/* Model Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <Cpu className="w-5 h-5 text-brand-600" />
                      <h3 className="text-lg font-semibold text-neutral-900">
                        {model.display_name}
                      </h3>
                    </div>
                    <p className="text-sm text-neutral-600 mb-2">{model.name}</p>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs px-2 py-1 bg-neutral-100 text-neutral-700 rounded">
                        {model.provider}
                      </span>
                      {model.supports_vision && (
                        <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                          Vision
                        </span>
                      )}
                      {model.is_enabled ? (
                        <span className="text-xs px-2 py-1 bg-success-100 text-success-700 rounded">
                          Aktiv
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-1 bg-neutral-100 text-neutral-700 rounded">
                          Inaktiv
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Model Details */}
                {model.description && (
                  <p className="text-sm text-neutral-600 mb-4">{model.description}</p>
                )}

                <div className="space-y-2 mb-4">
                  {model.max_tokens && (
                    <div className="flex justify-between text-sm">
                      <span className="text-neutral-600">Max Tokens:</span>
                      <span className="font-medium text-neutral-900">
                        {formatNumber(model.max_tokens)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Pricing Section */}
                <div className="border-t border-neutral-200 pt-4 mt-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <DollarSign className="w-4 h-4 text-brand-600" />
                    <h4 className="text-sm font-semibold text-neutral-900">Preise (pro 1M Tokens)</h4>
                  </div>

                  {isEditing ? (
                    <div className="space-y-3">
                      {/* Input Price */}
                      <div>
                        <label className="block text-xs font-medium text-neutral-700 mb-1">
                          Input Preis (USD)
                        </label>
                        <input
                          type="number"
                          step="0.0001"
                          min="0"
                          value={
                            editingModel.price_input_per_1m_tokens === null
                              ? ''
                              : editingModel.price_input_per_1m_tokens
                          }
                          onChange={e => {
                            const value = e.target.value;
                            setEditingModel({
                              ...editingModel,
                              price_input_per_1m_tokens:
                                value === '' ? null : parseFloat(value),
                            });
                          }}
                          placeholder="0.0000"
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                        />
                      </div>

                      {/* Output Price */}
                      <div>
                        <label className="block text-xs font-medium text-neutral-700 mb-1">
                          Output Preis (USD)
                        </label>
                        <input
                          type="number"
                          step="0.0001"
                          min="0"
                          value={
                            editingModel.price_output_per_1m_tokens === null
                              ? ''
                              : editingModel.price_output_per_1m_tokens
                          }
                          onChange={e => {
                            const value = e.target.value;
                            setEditingModel({
                              ...editingModel,
                              price_output_per_1m_tokens:
                                value === '' ? null : parseFloat(value),
                            });
                          }}
                          placeholder="0.0000"
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                        />
                      </div>

                      {/* Action Buttons */}
                      <div className="flex items-center space-x-2 pt-2">
                        <button
                          onClick={() => handleSave(model.id)}
                          disabled={isSaving}
                          className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {isSaving ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span>Speichern...</span>
                            </>
                          ) : (
                            <>
                              <Save className="w-4 h-4" />
                              <span>Speichern</span>
                            </>
                          )}
                        </button>
                        <button
                          onClick={handleCancel}
                          disabled={isSaving}
                          className="px-4 py-2 border border-neutral-300 text-neutral-700 rounded-lg hover:bg-neutral-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex justify-between items-center py-2">
                        <span className="text-sm text-neutral-600">Input:</span>
                        <span className="text-sm font-medium text-neutral-900">
                          {formatPrice(model.price_input_per_1m_tokens)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-2">
                        <span className="text-sm text-neutral-600">Output:</span>
                        <span className="text-sm font-medium text-neutral-900">
                          {formatPrice(model.price_output_per_1m_tokens)}
                        </span>
                      </div>
                      <button
                        onClick={() => handleEdit(model)}
                        className="w-full mt-3 px-4 py-2 border border-brand-300 text-brand-700 rounded-lg hover:bg-brand-50 transition-colors"
                      >
                        Preise bearbeiten
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AIModelManager;

