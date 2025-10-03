/**
 * Step Editor Modal Component
 *
 * Modal for creating/editing pipeline steps with:
 * - Prompt template editor (with syntax highlighting if Monaco is available)
 * - Model selection
 * - Temperature and max_tokens configuration
 * - Enable/disable toggle
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Save,
  AlertCircle,
  Settings,
  Brain,
  Thermometer,
  FileText,
  ToggleLeft,
  ToggleRight,
  Loader2,
  GitBranch,
  Tag
} from 'lucide-react';
import { pipelineApi } from '../../services/pipelineApi';
import { PipelineStep, AIModel, PipelineStepRequest, DocumentClass } from '../../types/pipeline';

interface StepEditorModalProps {
  step: PipelineStep | null; // null for creating new step
  models: AIModel[];
  documentClasses: DocumentClass[]; // NEW: For document class selection
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

const StepEditorModal: React.FC<StepEditorModalProps> = ({
  step,
  models,
  documentClasses,
  isOpen,
  onClose,
  onSave
}) => {
  // Form State
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [order, setOrder] = useState(1);
  const [enabled, setEnabled] = useState(true);
  const [promptTemplate, setPromptTemplate] = useState('');
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState<number | null>(null);
  const [retryOnFailure, setRetryOnFailure] = useState(true);
  const [maxRetries, setMaxRetries] = useState(3);
  const [inputFromPreviousStep, setInputFromPreviousStep] = useState(true);
  const [outputFormat, setOutputFormat] = useState<string>('text');

  // NEW: Branching fields
  const [documentClassId, setDocumentClassId] = useState<number | null>(null);
  const [isBranchingStep, setIsBranchingStep] = useState(false);
  const [branchingField, setBranchingField] = useState<string>('document_type');

  // UI State
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [validationError, setValidationError] = useState('');

  // Initialize form with step data or defaults
  useEffect(() => {
    if (step) {
      // Editing existing step
      setName(step.name);
      setDescription(step.description || '');
      setOrder(step.order);
      setEnabled(step.enabled);
      setPromptTemplate(step.prompt_template);
      setSelectedModelId(step.selected_model_id);
      setTemperature(step.temperature || 0.7);
      setMaxTokens(step.max_tokens);
      setRetryOnFailure(step.retry_on_failure);
      setMaxRetries(step.max_retries);
      setInputFromPreviousStep(step.input_from_previous_step);
      setOutputFormat(step.output_format || 'text');
      // NEW: Branching fields
      setDocumentClassId(step.document_class_id);
      setIsBranchingStep(step.is_branching_step);
      setBranchingField(step.branching_field || 'document_type');
    } else {
      // Creating new step - set defaults
      setName('');
      setDescription('');
      setOrder(1);
      setEnabled(true);
      setPromptTemplate('Bearbeiten Sie den folgenden Text:\n\n{input_text}\n\nGeben Sie das Ergebnis zurück.');
      setSelectedModelId(models.length > 0 ? models[0].id : null);
      setTemperature(0.7);
      setMaxTokens(null);
      setRetryOnFailure(true);
      setMaxRetries(3);
      setInputFromPreviousStep(true);
      setOutputFormat('text');
      // NEW: Branching field defaults
      setDocumentClassId(null);
      setIsBranchingStep(false);
      setBranchingField('document_type');
    }
  }, [step, models]);

  // Validate form
  const validateForm = (): boolean => {
    setValidationError('');

    if (!name.trim()) {
      setValidationError('Name ist erforderlich');
      return false;
    }

    if (!promptTemplate.trim()) {
      setValidationError('Prompt-Vorlage ist erforderlich');
      return false;
    }

    if (!promptTemplate.includes('{input_text}')) {
      setValidationError('Prompt-Vorlage muss {input_text} enthalten');
      return false;
    }

    if (selectedModelId === null) {
      setValidationError('Bitte wählen Sie ein Modell aus');
      return false;
    }

    if (order < 1) {
      setValidationError('Reihenfolge muss mindestens 1 sein');
      return false;
    }

    return true;
  };

  // Handle save
  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    setSaving(true);
    setError('');

    try {
      const stepData: PipelineStepRequest = {
        name: name.trim(),
        description: description.trim() || null,
        order,
        enabled,
        prompt_template: promptTemplate,
        selected_model_id: selectedModelId!,
        temperature,
        max_tokens: maxTokens,
        retry_on_failure: retryOnFailure,
        max_retries: maxRetries,
        input_from_previous_step: inputFromPreviousStep,
        output_format: outputFormat,
        // NEW: Branching fields
        document_class_id: documentClassId,
        is_branching_step: isBranchingStep,
        branching_field: isBranchingStep ? branchingField : null
      };

      if (step) {
        // Update existing step
        await pipelineApi.updateStep(step.id, stepData);
      } else {
        // Create new step
        await pipelineApi.createStep(stepData);
      }

      onSave();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-primary-200 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-primary-200 bg-gradient-to-r from-brand-50 to-accent-50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center">
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-primary-900">
                {step ? 'Schritt bearbeiten' : 'Neuen Schritt erstellen'}
              </h2>
              <p className="text-sm text-primary-600">
                Konfigurieren Sie einen Pipeline-Verarbeitungsschritt
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-primary-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-primary-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Error Messages */}
          {(error || validationError) && (
            <div className="flex items-center space-x-2 p-4 bg-error-50 border border-error-200 rounded-lg text-error-700">
              <AlertCircle className="w-5 h-5" />
              <span>{error || validationError}</span>
            </div>
          )}

          {/* Basic Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-primary-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                placeholder="z.B. Medical Validation"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-primary-700 mb-2">
                Reihenfolge *
              </label>
              <input
                type="number"
                value={order}
                onChange={(e) => setOrder(parseInt(e.target.value) || 1)}
                min="1"
                className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2">
              Beschreibung
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
              placeholder="Kurze Beschreibung des Schritts"
            />
          </div>

          {/* Prompt Template */}
          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2 flex items-center space-x-2">
              <FileText className="w-4 h-4" />
              <span>Prompt-Vorlage * (muss {'{input_text}'} enthalten)</span>
            </label>
            <textarea
              value={promptTemplate}
              onChange={(e) => setPromptTemplate(e.target.value)}
              rows={10}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none font-mono text-sm"
              placeholder="Ihr Prompt hier... Verwenden Sie {input_text} für den Eingabetext."
              required
            />
            <p className="text-xs text-primary-500 mt-1">
              Verfügbare Platzhalter: {'{input_text}'}, {'{target_language}'} (falls anwendbar)
            </p>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2 flex items-center space-x-2">
              <Brain className="w-4 h-4" />
              <span>AI-Modell *</span>
            </label>
            <select
              value={selectedModelId || ''}
              onChange={(e) => setSelectedModelId(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
              required
            >
              <option value="">Modell auswählen...</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.display_name} ({model.provider})
                  {model.max_tokens && ` - Max: ${model.max_tokens} tokens`}
                </option>
              ))}
            </select>
          </div>

          {/* Model Parameters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-primary-700 mb-2 flex items-center space-x-2">
                <Thermometer className="w-4 h-4" />
                <span>Temperatur: {temperature.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-primary-500 mt-1">
                <span>Präzise (0.0)</span>
                <span>Kreativ (2.0)</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-primary-700 mb-2">
                Max Tokens (optional)
              </label>
              <input
                type="number"
                value={maxTokens || ''}
                onChange={(e) => setMaxTokens(e.target.value ? parseInt(e.target.value) : null)}
                min="100"
                max="16000"
                className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                placeholder="Standard des Modells verwenden"
              />
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="border-t border-primary-200 pt-6">
            <h4 className="font-semibold text-primary-900 mb-4">Erweiterte Einstellungen</h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(e) => setEnabled(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-primary-700">Schritt aktiviert</span>
                </label>
              </div>

              <div>
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={retryOnFailure}
                    onChange={(e) => setRetryOnFailure(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-primary-700">Bei Fehler wiederholen</span>
                </label>
              </div>

              {retryOnFailure && (
                <div>
                  <label className="block text-sm font-medium text-primary-700 mb-2">
                    Max. Wiederholungen
                  </label>
                  <input
                    type="number"
                    value={maxRetries}
                    onChange={(e) => setMaxRetries(parseInt(e.target.value) || 0)}
                    min="0"
                    max="10"
                    className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-primary-700 mb-2">
                  Ausgabeformat
                </label>
                <select
                  value={outputFormat}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                >
                  <option value="text">Text</option>
                  <option value="json">JSON</option>
                  <option value="markdown">Markdown</option>
                </select>
              </div>
            </div>
          </div>

          {/* Pipeline Branching Settings */}
          <div className="border-t border-primary-200 pt-6">
            <h4 className="font-semibold text-primary-900 mb-4 flex items-center space-x-2">
              <GitBranch className="w-5 h-5 text-brand-600" />
              <span>Pipeline-Verzweigung</span>
            </h4>

            <div className="space-y-4">
              {/* Document Class Selection */}
              <div>
                <label className="block text-sm font-medium text-primary-700 mb-2 flex items-center space-x-2">
                  <Tag className="w-4 h-4" />
                  <span>Dokumentenklasse</span>
                </label>
                <select
                  value={documentClassId || ''}
                  onChange={(e) => setDocumentClassId(e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                >
                  <option value="">Universal (für alle Dokumenttypen)</option>
                  {documentClasses.map((docClass) => (
                    <option key={docClass.id} value={docClass.id}>
                      {docClass.icon} {docClass.display_name} ({docClass.class_key})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-primary-500 mt-1">
                  Wählen Sie eine Dokumentenklasse für klassenspezifische Schritte oder lassen Sie es leer für universelle Schritte
                </p>
              </div>

              {/* Branching Step Checkbox */}
              <div>
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isBranchingStep}
                    onChange={(e) => setIsBranchingStep(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-primary-700 flex items-center space-x-2">
                    <GitBranch className="w-4 h-4" />
                    <span>Klassifizierungs-Schritt (verzweigt Pipeline)</span>
                  </span>
                </label>
                <p className="text-xs text-primary-500 mt-1 ml-7">
                  Aktivieren Sie dies für den Schritt, der die Dokumentklasse bestimmt und die Pipeline verzweigt
                </p>
              </div>

              {/* Branching Field (only shown if branching step is enabled) */}
              {isBranchingStep && (
                <div className="ml-7 p-4 bg-brand-50 border border-brand-200 rounded-lg">
                  <label className="block text-sm font-medium text-brand-700 mb-2">
                    Verzweigungs-Feldname
                  </label>
                  <input
                    type="text"
                    value={branchingField}
                    onChange={(e) => setBranchingField(e.target.value)}
                    className="w-full px-3 py-2 border border-brand-300 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none font-mono text-sm"
                    placeholder="document_type"
                  />
                  <p className="text-xs text-brand-600 mt-1">
                    Das Feld in der Ausgabe, das den Klassenschlüssel enthält (Standard: "document_type")
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-primary-200 bg-neutral-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-primary-700 hover:bg-primary-100 rounded-lg transition-colors"
          >
            Abbrechen
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary flex items-center space-x-2"
          >
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>{step ? 'Speichern' : 'Erstellen'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default StepEditorModal;
