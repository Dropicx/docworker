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
  Loader2,
  GitBranch,
  Tag,
  Boxes,
} from 'lucide-react';
import { pipelineApi } from '../../services/pipelineApi';
import { PipelineStep, AIModel, PipelineStepRequest, DocumentClass } from '../../types/pipeline';

interface StepEditorModalProps {
  step: PipelineStep | null; // null for creating new step
  models: AIModel[];
  documentClasses: DocumentClass[]; // NEW: For document class selection
  defaultDocumentClassId?: number | null; // NEW: Pre-fill based on active tab
  defaultPostBranching?: boolean; // NEW: Pre-fill post_branching flag based on active tab
  pipelineContext?: string; // NEW: Display context in header (e.g., "Universal" or "📨 ARZTBRIEF")
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

const StepEditorModal: React.FC<StepEditorModalProps> = ({
  step,
  models,
  documentClasses,
  defaultDocumentClassId,
  defaultPostBranching = false,
  pipelineContext,
  isOpen,
  onClose,
  onSave,
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
  const [postBranching, setPostBranching] = useState(false); // NEW: Post-branching flag

  // NEW: Conditional execution
  const [requiredContextVariables, setRequiredContextVariables] = useState<string[]>([]);
  const [newVariable, setNewVariable] = useState('');

  // NEW: Stop conditions (termination)
  const [stopOnValues, setStopOnValues] = useState<string[]>([]);
  const [newStopValue, setNewStopValue] = useState('');
  const [terminationReason, setTerminationReason] = useState('');
  const [terminationMessage, setTerminationMessage] = useState('');

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
      setPostBranching(step.post_branching || false);
      // NEW: Conditional execution
      setRequiredContextVariables(step.required_context_variables || []);
      // NEW: Stop conditions
      if (step.stop_conditions) {
        setStopOnValues(step.stop_conditions.stop_on_values || []);
        setTerminationReason(step.stop_conditions.termination_reason || '');
        setTerminationMessage(step.stop_conditions.termination_message || '');
      } else {
        setStopOnValues([]);
        setTerminationReason('');
        setTerminationMessage('');
      }
    } else {
      // Creating new step - set defaults
      setName('');
      setDescription('');
      setOrder(1);
      setEnabled(true);
      setPromptTemplate(
        'Bearbeiten Sie den folgenden Text:\n\n{input_text}\n\nGeben Sie das Ergebnis zurück.'
      );
      setSelectedModelId(models.length > 0 ? models[0].id : null);
      setTemperature(0.7);
      setMaxTokens(null);
      setRetryOnFailure(true);
      setMaxRetries(3);
      setInputFromPreviousStep(true);
      setOutputFormat('text');
      // NEW: Branching field defaults - pre-fill document_class_id from active tab context
      setDocumentClassId(defaultDocumentClassId !== undefined ? defaultDocumentClassId : null);
      setIsBranchingStep(false);
      setBranchingField('document_type');
      setPostBranching(defaultPostBranching); // NEW: Pre-fill from active tab
      // NEW: Conditional execution defaults
      setRequiredContextVariables([]);
      // NEW: Stop conditions defaults
      setStopOnValues([]);
      setTerminationReason('');
      setTerminationMessage('');
    }
    setNewVariable(''); // Reset input field
    setNewStopValue(''); // Reset stop value input field
  }, [step, models, defaultDocumentClassId, defaultPostBranching]);

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
        branching_field: isBranchingStep ? branchingField : null,
        post_branching: postBranching, // NEW: Post-branching flag
        // NEW: Conditional execution
        required_context_variables:
          requiredContextVariables.length > 0 ? requiredContextVariables : null,
        // NEW: Stop conditions
        stop_conditions:
          stopOnValues.length > 0
            ? {
                stop_on_values: stopOnValues,
                termination_reason: terminationReason || 'Pipeline stopped',
                termination_message: terminationMessage || 'Die Verarbeitung wurde gestoppt.',
              }
            : null,
      };

      if (step) {
        // Update existing step
        await pipelineApi.updateStep(step.id, stepData);
      } else {
        // Create new step
        await pipelineApi.createStep(stepData);
      }

      onSave();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

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
                {step ? (
                  'Konfigurieren Sie einen Pipeline-Verarbeitungsschritt'
                ) : pipelineContext ? (
                  <>
                    Erstelle Schritt für:{' '}
                    <span className="font-semibold text-brand-700">{pipelineContext} Pipeline</span>
                  </>
                ) : (
                  'Konfigurieren Sie einen Pipeline-Verarbeitungsschritt'
                )}
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
              <label className="block text-sm font-medium text-primary-700 mb-2">Name *</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
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
                onChange={e => setOrder(parseInt(e.target.value) || 1)}
                min="1"
                className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2">Beschreibung</label>
            <input
              type="text"
              value={description}
              onChange={e => setDescription(e.target.value)}
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
              onChange={e => setPromptTemplate(e.target.value)}
              rows={10}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none font-mono text-sm"
              placeholder="Ihr Prompt hier... Verwenden Sie {input_text} für den Eingabetext."
              required
            />
            <div className="mt-2 p-3 bg-brand-50 border border-brand-200 rounded-lg">
              <p className="text-xs font-semibold text-brand-900 mb-2">📝 Verfügbare Variablen:</p>
              <div className="grid grid-cols-1 gap-2 text-xs text-brand-700">
                <div>
                  <code className="px-1.5 py-0.5 bg-brand-100 rounded font-mono">
                    {'{input_text}'}
                  </code>
                  <span className="ml-2">Ausgabe des vorherigen Schritts (wird überschrieben)</span>
                </div>
                <div>
                  <code className="px-1.5 py-0.5 bg-brand-100 rounded font-mono">
                    {'{original_text}'}
                  </code>{' '}
                  /{' '}
                  <code className="px-1.5 py-0.5 bg-brand-100 rounded font-mono">
                    {'{ocr_text}'}
                  </code>
                  <span className="ml-2">
                    🔒 OCR-Text nach PII-Entfernung (datenschutzsicher, bleibt immer verfügbar)
                  </span>
                </div>
                <div>
                  <code className="px-1.5 py-0.5 bg-brand-100 rounded font-mono">
                    {'{target_language}'}
                  </code>
                  <span className="ml-2">Zielsprache (falls vom Benutzer angegeben)</span>
                </div>
                <div>
                  <code className="px-1.5 py-0.5 bg-brand-100 rounded font-mono">
                    {'{document_type}'}
                  </code>
                  <span className="ml-2">Dokumenttyp (nach Klassifizierungs-Schritt)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-primary-700 mb-2 flex items-center space-x-2">
              <Brain className="w-4 h-4" />
              <span>AI-Modell *</span>
            </label>
            <select
              value={selectedModelId || ''}
              onChange={e => setSelectedModelId(parseInt(e.target.value))}
              className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
              required
            >
              <option value="">Modell auswählen...</option>
              {models.map(model => (
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
                onChange={e => setTemperature(parseFloat(e.target.value))}
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
                onChange={e => setMaxTokens(e.target.value ? parseInt(e.target.value) : null)}
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
                    onChange={e => setEnabled(e.target.checked)}
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
                    onChange={e => setRetryOnFailure(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-primary-700">
                    Bei Fehler wiederholen
                  </span>
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
                    onChange={e => setMaxRetries(parseInt(e.target.value) || 0)}
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
                  onChange={e => setOutputFormat(e.target.value)}
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
                  {step && (
                    <span className="text-xs text-warning-600 font-normal">
                      (Änderung nicht empfohlen)
                    </span>
                  )}
                </label>
                <select
                  value={documentClassId || ''}
                  onChange={e =>
                    setDocumentClassId(e.target.value ? parseInt(e.target.value) : null)
                  }
                  disabled={step !== null}
                  className={`w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none ${
                    step !== null ? 'bg-neutral-100 cursor-not-allowed opacity-75' : ''
                  }`}
                  title={
                    step
                      ? 'Dokumentenklasse kann bei bestehenden Schritten nicht geändert werden'
                      : ''
                  }
                >
                  <option value="">Universal (für alle Dokumenttypen)</option>
                  {documentClasses.map(docClass => (
                    <option key={docClass.id} value={docClass.id}>
                      {docClass.icon} {docClass.display_name} ({docClass.class_key})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-primary-500 mt-1">
                  {step
                    ? '⚠️ Die Dokumentenklasse ist bei bestehenden Schritten fixiert, um Pipeline-Konsistenz zu gewährleisten'
                    : 'Wählen Sie eine Dokumentenklasse für klassenspezifische Schritte oder lassen Sie es leer für universelle Schritte'}
                </p>
              </div>

              {/* Branching Step Checkbox */}
              <div>
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isBranchingStep}
                    onChange={e => setIsBranchingStep(e.target.checked)}
                    className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                  />
                  <span className="text-sm font-medium text-primary-700 flex items-center space-x-2">
                    <GitBranch className="w-4 h-4" />
                    <span>Klassifizierungs-Schritt (verzweigt Pipeline)</span>
                  </span>
                </label>
                <p className="text-xs text-primary-500 mt-1 ml-7">
                  Aktivieren Sie dies für den Schritt, der die Dokumentklasse bestimmt und die
                  Pipeline verzweigt
                </p>

                {/* Warning for universal step as branching point */}
                {isBranchingStep && documentClassId === null && (
                  <div className="ml-7 mt-3 p-3 bg-warning-50 border border-warning-300 rounded-lg flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-warning-600 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-warning-700">
                      <p className="font-semibold mb-1">⚠️ Verzweigungs-Schritt ist universal</p>
                      <p>
                        Dieser Schritt läuft für <strong>alle Dokumenttypen</strong> und leitet dann
                        zu klassenspezifischen Schritten weiter. Stellen Sie sicher, dass Ihr Prompt
                        das Feld{' '}
                        <code className="px-1 py-0.5 bg-warning-100 rounded font-mono">
                          {branchingField}
                        </code>{' '}
                        mit einem gültigen Klassenschlüssel zurückgibt.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Post-Branching Checkbox (only for universal steps) */}
              {documentClassId === null && !isBranchingStep && (
                <div>
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={postBranching}
                      onChange={e => setPostBranching(e.target.checked)}
                      className="w-4 h-4 text-brand-600 border-primary-300 rounded focus:ring-brand-500"
                    />
                    <span className="text-sm font-medium text-primary-700 flex items-center space-x-2">
                      <Boxes className="w-4 h-4" />
                      <span>Nach dokumentspezifischen Schritten ausführen</span>
                    </span>
                  </label>
                  <p className="text-xs text-primary-500 mt-1 ml-7">
                    Aktivieren Sie dies für universelle Schritte, die NACH der dokumentspezifischen
                    Verarbeitung laufen sollen (z.B. Übersetzung, Formatierung)
                  </p>
                </div>
              )}

              {/* Branching Field (only shown if branching step is enabled) */}
              {isBranchingStep && (
                <div className="ml-7 p-4 bg-brand-50 border border-brand-200 rounded-lg">
                  <label className="block text-sm font-medium text-brand-700 mb-2">
                    Verzweigungs-Feldname
                  </label>
                  <input
                    type="text"
                    value={branchingField}
                    onChange={e => setBranchingField(e.target.value)}
                    className="w-full px-3 py-2 border border-brand-300 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none font-mono text-sm"
                    placeholder="document_type"
                  />
                  <p className="text-xs text-brand-600 mt-1">
                    Das Feld in der Ausgabe, das den Klassenschlüssel enthält (Standard:
                    &quot;document_type&quot;)
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Conditional Execution Settings */}
          <div className="border-t border-primary-200 pt-6">
            <h4 className="font-semibold text-primary-900 mb-4 flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-brand-600" />
              <span>Bedingte Ausführung</span>
            </h4>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-primary-600 mb-3">
                  Definieren Sie Kontextvariablen, die vorhanden sein müssen, damit dieser Schritt
                  ausgeführt wird. Wenn eine Variable fehlt, wird der Schritt übersprungen.
                </p>

                {/* List of required variables */}
                {requiredContextVariables.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {requiredContextVariables.map((variable, index) => (
                      <div
                        key={index}
                        className="inline-flex items-center space-x-2 px-3 py-1.5 bg-brand-50 border border-brand-200 rounded-lg"
                      >
                        <code className="text-sm font-mono text-brand-700">{variable}</code>
                        <button
                          onClick={() => {
                            setRequiredContextVariables(prev => prev.filter((_, i) => i !== index));
                          }}
                          className="text-brand-600 hover:text-brand-800 transition-colors"
                          title="Variable entfernen"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add new variable */}
                <div className="flex items-center space-x-2">
                  <input
                    type="text"
                    value={newVariable}
                    onChange={e => setNewVariable(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        const trimmed = newVariable.trim();
                        if (trimmed && !requiredContextVariables.includes(trimmed)) {
                          setRequiredContextVariables(prev => [...prev, trimmed]);
                          setNewVariable('');
                        }
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none font-mono text-sm"
                    placeholder="z.B. target_language"
                  />
                  <button
                    onClick={() => {
                      const trimmed = newVariable.trim();
                      if (trimmed && !requiredContextVariables.includes(trimmed)) {
                        setRequiredContextVariables(prev => [...prev, trimmed]);
                        setNewVariable('');
                      }
                    }}
                    disabled={
                      !newVariable.trim() || requiredContextVariables.includes(newVariable.trim())
                    }
                    className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Variable hinzufügen"
                  >
                    Hinzufügen
                  </button>
                </div>

                {/* Help text */}
                <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-xs font-semibold text-blue-900 mb-2">
                    💡 Verfügbare Kontextvariablen:
                  </p>
                  <div className="grid grid-cols-1 gap-2 text-xs text-blue-700">
                    <div>
                      <code className="px-1.5 py-0.5 bg-blue-100 rounded font-mono">
                        target_language
                      </code>
                      <span className="ml-2">Zielsprache für Übersetzung</span>
                    </div>
                    <div>
                      <code className="px-1.5 py-0.5 bg-blue-100 rounded font-mono">
                        document_type
                      </code>
                      <span className="ml-2">Dokumenttyp (nach Klassifizierung)</span>
                    </div>
                    <div>
                      <code className="px-1.5 py-0.5 bg-blue-100 rounded font-mono">
                        original_text
                      </code>
                      <span className="ml-2">OCR-Text (immer verfügbar)</span>
                    </div>
                  </div>
                </div>

                {/* Example warning */}
                {requiredContextVariables.includes('target_language') && (
                  <div className="mt-3 p-3 bg-brand-50 border border-brand-200 rounded-lg flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-brand-700">
                      <p className="font-semibold mb-1">ℹ️ Hinweis</p>
                      <p>
                        Dieser Schritt wird übersprungen, wenn der Benutzer keine Zielsprache
                        auswählt. Der Schritt wird im Audit-Log als SKIPPED markiert.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Stop Conditions (Early Termination) */}
          <div className="border-t border-primary-200 pt-6">
            <h4 className="font-semibold text-primary-900 mb-4 flex items-center space-x-2">
              <AlertCircle className="w-5 h-5 text-error-600" />
              <span>Stop-Bedingungen (Pipeline-Abbruch)</span>
            </h4>

            <div className="space-y-4">
              <div>
                <p className="text-sm text-primary-600 mb-3">
                  Definieren Sie Ausgabewerte, die die Pipeline sofort beenden sollen (z.B.
                  NICHT_MEDIZINISCH). Die Pipeline wird gestoppt und der Benutzer erhält eine
                  benutzerdefinierte Nachricht.
                </p>

                {/* List of stop values */}
                {stopOnValues.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-2">
                    {stopOnValues.map((value, index) => (
                      <div
                        key={index}
                        className="inline-flex items-center space-x-2 px-3 py-1.5 bg-error-50 border border-error-200 rounded-lg"
                      >
                        <code className="text-sm font-mono text-error-700">{value}</code>
                        <button
                          onClick={() => {
                            setStopOnValues(prev => prev.filter((_, i) => i !== index));
                          }}
                          className="text-error-600 hover:text-error-800 transition-colors"
                          title="Wert entfernen"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add new stop value */}
                <div className="flex items-center space-x-2 mb-4">
                  <input
                    type="text"
                    value={newStopValue}
                    onChange={e => setNewStopValue(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        const trimmed = newStopValue.trim().toUpperCase();
                        if (trimmed && !stopOnValues.includes(trimmed)) {
                          setStopOnValues(prev => [...prev, trimmed]);
                          setNewStopValue('');
                        }
                      }
                    }}
                    className="flex-1 px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none font-mono text-sm"
                    placeholder="z.B. NICHT_MEDIZINISCH"
                  />
                  <button
                    onClick={() => {
                      const trimmed = newStopValue.trim().toUpperCase();
                      if (trimmed && !stopOnValues.includes(trimmed)) {
                        setStopOnValues(prev => [...prev, trimmed]);
                        setNewStopValue('');
                      }
                    }}
                    disabled={
                      !newStopValue.trim() ||
                      stopOnValues.includes(newStopValue.trim().toUpperCase())
                    }
                    className="px-4 py-2 bg-error-600 text-white rounded-lg hover:bg-error-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Wert hinzufügen"
                  >
                    Hinzufügen
                  </button>
                </div>

                {/* Termination reason and message (only shown if stop values exist) */}
                {stopOnValues.length > 0 && (
                  <div className="space-y-3 p-4 bg-error-50 border border-error-200 rounded-lg">
                    <div>
                      <label className="block text-sm font-medium text-error-900 mb-2">
                        Abbruchgrund (technisch)
                      </label>
                      <input
                        type="text"
                        value={terminationReason}
                        onChange={e => setTerminationReason(e.target.value)}
                        className="w-full px-3 py-2 border border-error-300 rounded-lg focus:border-error-500 focus:ring-2 focus:ring-error-100 focus:outline-none"
                        placeholder="z.B. Non-medical content detected"
                      />
                      <p className="text-xs text-error-600 mt-1">Wird im Audit-Log gespeichert</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-error-900 mb-2">
                        Benutzer-Nachricht (wird dem Benutzer angezeigt)
                      </label>
                      <textarea
                        value={terminationMessage}
                        onChange={e => setTerminationMessage(e.target.value)}
                        rows={3}
                        className="w-full px-3 py-2 border border-error-300 rounded-lg focus:border-error-500 focus:ring-2 focus:ring-error-100 focus:outline-none"
                        placeholder="z.B. Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument hoch."
                      />
                      <p className="text-xs text-error-600 mt-1">
                        Diese Nachricht wird im Frontend angezeigt
                      </p>
                    </div>
                  </div>
                )}

                {/* Matching Preview */}
                {stopOnValues.length > 0 && (
                  <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-xs font-semibold text-blue-900 mb-2">
                      🔍 Matching-Vorschau (nur ERSTES WORT wird geprüft)
                    </p>
                    <div className="space-y-2">
                      <div>
                        <p className="text-xs text-blue-700 font-medium mb-1">
                          Pipeline wird gestoppt, wenn die Ausgabe startet mit:
                        </p>
                        <div className="flex flex-wrap gap-1">
                          {stopOnValues.map((value, idx) => (
                            <code
                              key={idx}
                              className="px-2 py-0.5 bg-blue-100 border border-blue-300 rounded text-xs font-mono text-blue-800"
                            >
                              {value}
                            </code>
                          ))}
                        </div>
                      </div>
                      <div className="border-t border-blue-200 pt-2">
                        <p className="text-xs text-blue-700 font-medium mb-1">Beispiele:</p>
                        <ul className="text-xs text-blue-600 space-y-1">
                          <li className="flex items-start space-x-2">
                            <span className="text-green-600 font-bold">✓</span>
                            <span>
                              <code className="bg-green-50 px-1 rounded">
                                {stopOnValues[0] || 'STOP_VALUE'}
                              </code>{' '}
                              → Pipeline stoppt
                            </span>
                          </li>
                          <li className="flex items-start space-x-2">
                            <span className="text-green-600 font-bold">✓</span>
                            <span>
                              <code className="bg-green-50 px-1 rounded">
                                {stopOnValues[0] || 'STOP_VALUE'} - Details hier
                              </code>{' '}
                              → Pipeline stoppt
                            </span>
                          </li>
                          <li className="flex items-start space-x-2">
                            <span className="text-red-600 font-bold">✗</span>
                            <span>
                              <code className="bg-red-50 px-1 rounded">
                                Der Text ist {stopOnValues[0] || 'STOP_VALUE'}
                              </code>{' '}
                              → Pipeline läuft weiter
                            </span>
                          </li>
                        </ul>
                      </div>
                      <div className="border-t border-blue-200 pt-2">
                        <p className="text-xs text-blue-800 font-medium">
                          💡 Best Practice: Konfigurieren Sie Ihren Prompt so, dass der Stop-Wert
                          das ERSTE WORT ist
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                          Beispiel: &quot;Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH&quot;
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Help text */}
                <div className="mt-3 p-3 bg-warning-50 border border-warning-200 rounded-lg">
                  <p className="text-xs font-semibold text-warning-900 mb-2">⚠️ Wichtig:</p>
                  <ul className="text-xs text-warning-700 space-y-1 list-disc list-inside">
                    <li>Stop-Werte werden GROSS/klein-Schreibung ignorierend verglichen</li>
                    <li>Die Pipeline wird sofort nach diesem Schritt beendet</li>
                    <li>Nachfolgende Schritte werden nicht ausgeführt</li>
                    <li>Der Benutzer erhält eine benutzerfreundliche Fehlermeldung</li>
                  </ul>
                </div>

                {/* Example */}
                {stopOnValues.includes('NICHT_MEDIZINISCH') && (
                  <div className="mt-3 p-3 bg-brand-50 border border-brand-200 rounded-lg flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
                    <div className="text-xs text-brand-700">
                      <p className="font-semibold mb-1">💡 Beispiel-Anwendung</p>
                      <p>
                        Wenn dieser Schritt &quot;NICHT_MEDIZINISCH&quot; ausgibt, wird die Pipeline
                        sofort gestoppt. Der Benutzer sieht eine Warnung und kann ein anderes
                        Dokument hochladen. Dies spart API-Kosten und verbessert die
                        Benutzererfahrung.
                      </p>
                    </div>
                  </div>
                )}
              </div>
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
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span>{step ? 'Speichern' : 'Erstellen'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default StepEditorModal;
