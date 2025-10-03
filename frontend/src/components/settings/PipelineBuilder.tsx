/**
 * Pipeline Builder Component
 *
 * Allows users to configure:
 * - OCR engine selection
 * - Dynamic pipeline steps (add/edit/delete/reorder)
 */

import React, { useState, useEffect } from 'react';
import {
  Settings,
  Plus,
  Edit2,
  Trash2,
  Eye,
  EyeOff,
  GripVertical,
  AlertCircle,
  CheckCircle,
  Loader2,
  Save,
  RotateCcw,
  Zap,
  Brain,
  Image as ImageIcon,
  Boxes
} from 'lucide-react';
import { pipelineApi } from '../../services/pipelineApi';
import {
  OCRConfiguration,
  OCREngineEnum,
  PipelineStep,
  AIModel,
  EngineStatusMap,
  PipelineStepRequest
} from '../../types/pipeline';
import StepEditorModal from './StepEditorModal';

const PipelineBuilder: React.FC = () => {
  // OCR Configuration State
  const [ocrConfig, setOcrConfig] = useState<OCRConfiguration | null>(null);
  const [engines, setEngines] = useState<EngineStatusMap | null>(null);
  const [selectedEngine, setSelectedEngine] = useState<OCREngineEnum>(OCREngineEnum.HYBRID);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrSaving, setOcrSaving] = useState(false);

  // Pipeline Steps State
  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [stepsLoading, setStepsLoading] = useState(false);

  // AI Models State
  const [models, setModels] = useState<AIModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(false);

  // Step Editor Modal State
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingStep, setEditingStep] = useState<PipelineStep | null>(null);

  // UI State
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  // Load data on mount
  useEffect(() => {
    loadOCRConfig();
    loadEngines();
    loadSteps();
    loadModels();
  }, []);

  // ==================== DATA LOADING ====================

  const loadOCRConfig = async () => {
    setOcrLoading(true);
    try {
      const config = await pipelineApi.getOCRConfig();
      setOcrConfig(config);
      setSelectedEngine(config.selected_engine as OCREngineEnum);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setOcrLoading(false);
    }
  };

  const loadEngines = async () => {
    try {
      const enginesData = await pipelineApi.getAvailableEngines();
      setEngines(enginesData);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const loadSteps = async () => {
    setStepsLoading(true);
    try {
      const stepsData = await pipelineApi.getAllSteps();
      setSteps(stepsData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setStepsLoading(false);
    }
  };

  const loadModels = async () => {
    setModelsLoading(true);
    try {
      const modelsData = await pipelineApi.getAvailableModels(true);
      setModels(modelsData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setModelsLoading(false);
    }
  };

  // ==================== OCR ENGINE ACTIONS ====================

  const handleEngineChange = async (engine: OCREngineEnum) => {
    setSelectedEngine(engine);
  };

  const saveOCRConfig = async () => {
    setOcrSaving(true);
    setError('');
    setSuccess('');

    try {
      await pipelineApi.updateOCRConfig({
        selected_engine: selectedEngine,
        tesseract_config: ocrConfig?.tesseract_config || null,
        paddleocr_config: ocrConfig?.paddleocr_config || null,
        vision_llm_config: ocrConfig?.vision_llm_config || null,
        hybrid_config: ocrConfig?.hybrid_config || null
      });

      setSuccess('OCR-Konfiguration erfolgreich gespeichert!');
      await loadOCRConfig();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setOcrSaving(false);
    }
  };

  // ==================== PIPELINE STEP ACTIONS ====================

  const handleAddStep = () => {
    setEditingStep(null);
    setIsEditorOpen(true);
  };

  const handleEditStep = (step: PipelineStep) => {
    setEditingStep(step);
    setIsEditorOpen(true);
  };

  const handleDeleteStep = async (stepId: number) => {
    if (!confirm('Möchten Sie diesen Schritt wirklich löschen?')) {
      return;
    }

    try {
      await pipelineApi.deleteStep(stepId);
      setSuccess('Schritt erfolgreich gelöscht!');
      await loadSteps();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleToggleStep = async (step: PipelineStep) => {
    try {
      const updatedStep: PipelineStepRequest = {
        name: step.name,
        description: step.description,
        order: step.order,
        enabled: !step.enabled,
        prompt_template: step.prompt_template,
        selected_model_id: step.selected_model_id,
        temperature: step.temperature,
        max_tokens: step.max_tokens,
        retry_on_failure: step.retry_on_failure,
        max_retries: step.max_retries,
        input_from_previous_step: step.input_from_previous_step,
        output_format: step.output_format
      };

      await pipelineApi.updateStep(step.id, updatedStep);
      await loadSteps();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const toggleStepExpansion = (stepId: number) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId);
    } else {
      newExpanded.add(stepId);
    }
    setExpandedSteps(newExpanded);
  };

  // ==================== RENDER HELPERS ====================

  const getEngineIcon = (engine: string) => {
    switch (engine) {
      case 'TESSERACT':
        return <Zap className="w-5 h-5" />;
      case 'PADDLEOCR':
        return <Brain className="w-5 h-5" />;
      case 'VISION_LLM':
        return <ImageIcon className="w-5 h-5" />;
      case 'HYBRID':
        return <Boxes className="w-5 h-5" />;
      default:
        return <Settings className="w-5 h-5" />;
    }
  };

  const getModelName = (modelId: number): string => {
    const model = models.find(m => m.id === modelId);
    return model ? model.display_name : `Model ID ${modelId}`;
  };

  // ==================== RENDER ====================

  return (
    <div className="space-y-8">
      {/* Error/Success Messages */}
      {error && (
        <div className="flex items-center space-x-2 p-4 bg-error-50 border border-error-200 rounded-lg text-error-700">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="flex items-center space-x-2 p-4 bg-success-50 border border-success-200 rounded-lg text-success-700">
          <CheckCircle className="w-5 h-5" />
          <span>{success}</span>
        </div>
      )}

      {/* OCR Engine Configuration */}
      <div className="bg-white rounded-xl border border-primary-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-primary-900 flex items-center space-x-2">
              <ImageIcon className="w-5 h-5 text-brand-600" />
              <span>OCR-Engine Konfiguration</span>
            </h3>
            <p className="text-sm text-primary-600 mt-1">
              Wählen Sie die OCR-Engine für die Texterkennung
            </p>
          </div>
          <button
            onClick={saveOCRConfig}
            disabled={ocrSaving}
            className="btn-primary flex items-center space-x-2"
          >
            {ocrSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>Speichern</span>
          </button>
        </div>

        {ocrLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {engines && Object.entries(engines).map(([engineKey, engineInfo]) => {
              const isSelected = selectedEngine === engineKey;
              const isAvailable = engineInfo.available;

              return (
                <button
                  key={engineKey}
                  onClick={() => handleEngineChange(engineKey as OCREngineEnum)}
                  disabled={!isAvailable}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    isSelected
                      ? 'border-brand-500 bg-brand-50'
                      : isAvailable
                      ? 'border-primary-200 hover:border-brand-300 hover:bg-brand-50/50'
                      : 'border-primary-100 bg-neutral-50 opacity-50 cursor-not-allowed'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className={`${isSelected ? 'text-brand-600' : 'text-primary-600'}`}>
                      {getEngineIcon(engineKey)}
                    </div>
                    {!isAvailable && (
                      <span className="text-xs px-2 py-1 bg-neutral-200 text-neutral-600 rounded">
                        Nicht verfügbar
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-primary-900 mb-1">{engineInfo.engine}</h4>
                  <p className="text-xs text-primary-600 mb-2">{engineInfo.description}</p>
                  <div className="space-y-1 text-xs text-primary-500">
                    <div>⚡ {engineInfo.speed}</div>
                    <div>🎯 {engineInfo.accuracy}</div>
                    <div>💰 {engineInfo.cost}</div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Pipeline Steps */}
      <div className="bg-white rounded-xl border border-primary-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-primary-900 flex items-center space-x-2">
              <Settings className="w-5 h-5 text-brand-600" />
              <span>Pipeline-Schritte</span>
            </h3>
            <p className="text-sm text-primary-600 mt-1">
              Konfigurieren Sie die Verarbeitungsschritte Ihrer Pipeline
            </p>
          </div>
          <button
            onClick={handleAddStep}
            className="btn-primary flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Schritt hinzufügen</span>
          </button>
        </div>

        {stepsLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          </div>
        ) : steps.length === 0 ? (
          <div className="text-center py-8 text-primary-500">
            <p>Keine Pipeline-Schritte konfiguriert.</p>
            <p className="text-sm mt-2">Klicken Sie auf "Schritt hinzufügen", um zu beginnen.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {steps.map((step) => {
              const isExpanded = expandedSteps.has(step.id);

              return (
                <div
                  key={step.id}
                  className={`border rounded-lg transition-all ${
                    step.enabled
                      ? 'border-primary-200 bg-white'
                      : 'border-neutral-200 bg-neutral-50'
                  }`}
                >
                  {/* Step Header */}
                  <div className="p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4 flex-1">
                      <div className="cursor-move text-primary-400">
                        <GripVertical className="w-5 h-5" />
                      </div>

                      <div className="flex items-center space-x-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                          step.enabled ? 'bg-brand-100 text-brand-700' : 'bg-neutral-200 text-neutral-600'
                        }`}>
                          {step.order}
                        </div>

                        <div>
                          <div className="flex items-center space-x-2">
                            <h4 className={`font-semibold ${step.enabled ? 'text-primary-900' : 'text-neutral-600'}`}>
                              {step.name}
                            </h4>
                            {!step.enabled && (
                              <span className="text-xs px-2 py-1 bg-neutral-200 text-neutral-600 rounded">
                                Deaktiviert
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-primary-500 mt-1">{step.description}</p>
                          <div className="flex items-center space-x-4 mt-2 text-xs text-primary-500">
                            <span>🤖 {getModelName(step.selected_model_id)}</span>
                            <span>🌡️ Temp: {step.temperature?.toFixed(1) || '0.7'}</span>
                            {step.max_tokens && <span>📊 Max: {step.max_tokens}</span>}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => toggleStepExpansion(step.id)}
                        className="p-2 hover:bg-primary-100 rounded-lg transition-colors"
                        title={isExpanded ? "Einklappen" : "Aufklappen"}
                      >
                        {isExpanded ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>

                      <button
                        onClick={() => handleToggleStep(step)}
                        className={`p-2 rounded-lg transition-colors ${
                          step.enabled
                            ? 'hover:bg-warning-100 text-warning-600'
                            : 'hover:bg-success-100 text-success-600'
                        }`}
                        title={step.enabled ? "Deaktivieren" : "Aktivieren"}
                      >
                        <Settings className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => handleEditStep(step)}
                        className="p-2 hover:bg-brand-100 rounded-lg transition-colors text-brand-600"
                        title="Bearbeiten"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => handleDeleteStep(step.id)}
                        className="p-2 hover:bg-error-100 rounded-lg transition-colors text-error-600"
                        title="Löschen"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="border-t border-primary-200 p-4 bg-neutral-50">
                      <h5 className="font-semibold text-sm text-primary-900 mb-2">Prompt Template:</h5>
                      <pre className="text-xs bg-white border border-primary-200 rounded p-3 overflow-x-auto whitespace-pre-wrap text-primary-700">
                        {step.prompt_template}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Step Editor Modal */}
      {isEditorOpen && (
        <StepEditorModal
          step={editingStep}
          models={models}
          isOpen={isEditorOpen}
          onClose={() => {
            setIsEditorOpen(false);
            setEditingStep(null);
          }}
          onSave={async () => {
            setIsEditorOpen(false);
            setEditingStep(null);
            await loadSteps();
            setSuccess('Schritt erfolgreich gespeichert!');
            setTimeout(() => setSuccess(''), 3000);
          }}
        />
      )}
    </div>
  );
};

export default PipelineBuilder;
