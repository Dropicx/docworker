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
  Zap,
  Brain,
  Image as ImageIcon,
  Boxes,
  RefreshCw,
  Shield,
  Sparkles,
  BookOpen,
  Copy,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { pipelineApi } from '../../services/pipelineApi';
import {
  OCRConfiguration,
  OCREngineEnum,
  PipelineStep,
  AIModel,
  EngineStatusMap,
  PipelineStepRequest,
  DocumentClass,
} from '../../types/pipeline';
import StepEditorModal from './StepEditorModal';
import DuplicateStepModal from './DuplicateStepModal';

const PipelineBuilder: React.FC = () => {
  const { t } = useTranslation();

  // OCR Configuration State
  const [ocrConfig, setOcrConfig] = useState<OCRConfiguration | null>(null);
  const [engines, setEngines] = useState<EngineStatusMap | null>(null);
  const [selectedEngine, setSelectedEngine] = useState<OCREngineEnum>(OCREngineEnum.HYBRID);
  const [piiRemovalEnabled, setPiiRemovalEnabled] = useState<boolean>(true); // NEW: PII removal toggle
  const [guidelinesEnabled, setGuidelinesEnabled] = useState<boolean>(true); // AWMF guidelines toggle
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrSaving, setOcrSaving] = useState(false);

  // Pipeline Steps State
  const [steps, setSteps] = useState<PipelineStep[]>([]);
  const [stepsLoading, setStepsLoading] = useState(false);

  // AI Models State
  const [models, setModels] = useState<AIModel[]>([]);
  const [_modelsLoading, setModelsLoading] = useState(false);

  // Document Classes State (NEW)
  const [documentClasses, setDocumentClasses] = useState<DocumentClass[]>([]);
  const [classesLoading, setClassesLoading] = useState(false);

  // Step Editor Modal State
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingStep, setEditingStep] = useState<PipelineStep | null>(null);

  // Duplicate Step Modal State
  const [isDuplicateModalOpen, setIsDuplicateModalOpen] = useState(false);
  const [stepToDuplicate, setStepToDuplicate] = useState<PipelineStep | null>(null);

  // UI State
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  // Pipeline Tab State (NEW)
  const [activePipelineTab, setActivePipelineTab] = useState<
    'pre-branching' | 'post-branching' | number
  >('pre-branching');

  // Track previous document class count for notifications (NEW)
  const [prevClassCount, setPrevClassCount] = useState<number>(0);

  // Drag and Drop State
  const [draggedStep, setDraggedStep] = useState<PipelineStep | null>(null);
  const [draggedOverStep, setDraggedOverStep] = useState<PipelineStep | null>(null);

  // Load data on mount
  useEffect(() => {
    loadOCRConfig();
    loadEngines();
    loadSteps();
    loadModels();
    loadDocumentClasses(); // NEW
  }, []);

  // Track document class changes and show notification (NEW)
  useEffect(() => {
    if (prevClassCount > 0 && documentClasses.length > prevClassCount) {
      const newClassCount = documentClasses.length - prevClassCount;
      setSuccess(
        `✨ ${newClassCount} neue Dokumentklasse${newClassCount > 1 ? 'n' : ''} hinzugefügt! Neue Tabs sind jetzt verfügbar.`
      );
      setTimeout(() => setSuccess(''), 5000);
    }
    setPrevClassCount(documentClasses.length);
  }, [documentClasses.length, prevClassCount]);

  // ==================== DATA LOADING ====================

  const loadOCRConfig = async () => {
    setOcrLoading(true);
    try {
      const config = await pipelineApi.getOCRConfig();
      setOcrConfig(config);
      setSelectedEngine(config.selected_engine as OCREngineEnum);
      setPiiRemovalEnabled(config.pii_removal_enabled ?? true); // Load PII toggle state
      setGuidelinesEnabled(config.guidelines_analysis_enabled ?? true); // Load guidelines toggle state
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setOcrLoading(false);
    }
  };

  const loadEngines = async () => {
    try {
      const enginesData = await pipelineApi.getAvailableEngines();
      setEngines(enginesData);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const loadSteps = async () => {
    setStepsLoading(true);
    try {
      const stepsData = await pipelineApi.getAllSteps();
      setSteps(stepsData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStepsLoading(false);
    }
  };

  const loadModels = async () => {
    setModelsLoading(true);
    try {
      const modelsData = await pipelineApi.getAvailableModels(true);
      setModels(modelsData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setModelsLoading(false);
    }
  };

  const loadDocumentClasses = async () => {
    setClassesLoading(true);
    try {
      const classesData = await pipelineApi.getAllDocumentClasses(true); // Only enabled classes
      setDocumentClasses(classesData);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setClassesLoading(false);
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
        paddleocr_config: ocrConfig?.paddleocr_config || null,
        vision_llm_config: ocrConfig?.vision_llm_config || null,
        hybrid_config: ocrConfig?.hybrid_config || null,
        pii_removal_enabled: piiRemovalEnabled,
        guidelines_analysis_enabled: guidelinesEnabled,
      });

      setSuccess('OCR-Konfiguration erfolgreich gespeichert!');
      await loadOCRConfig();

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setOcrSaving(false);
    }
  };

  // ==================== PIPELINE STEP ACTIONS ====================

  const handleAddStep = () => {
    setEditingStep(null);
    setIsEditorOpen(true);
  };

  // Get default document class ID based on active tab context
  const getDefaultDocumentClassId = (): number | null => {
    if (activePipelineTab === 'pre-branching' || activePipelineTab === 'post-branching') {
      return null;
    }
    return activePipelineTab;
  };

  // Get default post_branching flag based on active tab context
  const getDefaultPostBranching = (): boolean => {
    return activePipelineTab === 'post-branching';
  };

  // Get step count for a specific document class or phase
  const getStepCount = (context: 'pre-branching' | 'post-branching' | number): number => {
    if (context === 'pre-branching') {
      return steps.filter(s => s.document_class_id === null && !s.post_branching).length;
    } else if (context === 'post-branching') {
      return steps.filter(s => s.document_class_id === null && s.post_branching).length;
    } else {
      return steps.filter(s => s.document_class_id === context).length;
    }
  };

  // Get filtered steps based on active tab
  const getDisplayedSteps = (): PipelineStep[] => {
    if (activePipelineTab === 'pre-branching') {
      return steps
        .filter(s => s.document_class_id === null && !s.post_branching)
        .sort((a, b) => a.order - b.order);
    } else if (activePipelineTab === 'post-branching') {
      return steps
        .filter(s => s.document_class_id === null && s.post_branching)
        .sort((a, b) => a.order - b.order);
    } else {
      return steps
        .filter(s => s.document_class_id === activePipelineTab)
        .sort((a, b) => a.order - b.order);
    }
  };

  // Get document class name by ID or context
  const getDocumentClassName = (
    classId: number | null | 'pre-branching' | 'post-branching' | 'universal'
  ): string => {
    if (classId === null || classId === 'universal') return 'Universal';
    if (classId === 'pre-branching') return 'Pre-Branching';
    if (classId === 'post-branching') return 'Post-Branching';
    const docClass = documentClasses.find(c => c.id === classId);
    return docClass ? `${docClass.icon} ${docClass.display_name}` : `Class ${classId}`;
  };

  const handleEditStep = (step: PipelineStep) => {
    setEditingStep(step);
    setIsEditorOpen(true);
  };

  const handleOpenDuplicateModal = (step: PipelineStep) => {
    setStepToDuplicate(step);
    setIsDuplicateModalOpen(true);
  };

  const handleDuplicateStep = async (newName: string, sourceLanguage: string | null) => {
    if (!stepToDuplicate) return;

    await pipelineApi.duplicateStep(stepToDuplicate.id, newName, sourceLanguage);
    await loadSteps();
    setSuccess(t('pipeline.duplicateSuccess', 'Schritt erfolgreich dupliziert'));
    setTimeout(() => setSuccess(''), 3000);
  };

  const handleDeleteStep = async (stepId: number) => {
    if (!confirm('Möchten Sie diesen Schritt wirklich löschen?')) {
      return;
    }

    try {
      // Optimistically remove from local state
      const newSteps = steps.filter(s => s.id !== stepId);
      setSteps(newSteps);

      // Persist to backend
      await pipelineApi.deleteStep(stepId);
      setSuccess('Schritt erfolgreich gelöscht!');

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError((err as Error).message);
      // Reload on error to restore correct state
      await loadSteps();
    }
  };

  const handleToggleStep = async (step: PipelineStep) => {
    try {
      const updatedStep: PipelineStepRequest = {
        name: step.name,
        description: step.description || null,
        order: step.order,
        enabled: !step.enabled,
        prompt_template: step.prompt_template,
        selected_model_id: step.selected_model_id,
        temperature: step.temperature ?? 0.7,
        max_tokens: step.max_tokens ?? null,
        retry_on_failure: step.retry_on_failure ?? true,
        max_retries: step.max_retries ?? 3,
        input_from_previous_step: step.input_from_previous_step ?? true,
        output_format: step.output_format || 'text',
        // Include branching fields to prevent unwanted changes
        document_class_id: step.document_class_id ?? null,
        is_branching_step: step.is_branching_step ?? false,
        branching_field: step.branching_field || null,
        post_branching: step.post_branching ?? false,
        // Additional fields
        required_context_variables: step.required_context_variables || null,
        stop_conditions: step.stop_conditions || null,
      };

      // Optimistically update local state first
      const newSteps = steps.map(s => (s.id === step.id ? { ...s, enabled: !s.enabled } : s));
      setSteps(newSteps);

      // Persist to backend (no await to keep UI responsive)
      pipelineApi.updateStep(step.id, updatedStep).catch(err => {
        // If API fails, reload to get correct state
        setError((err as Error).message);
        loadSteps();
      });
    } catch (err) {
      setError((err as Error).message);
      await loadSteps();
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

  // ==================== DRAG AND DROP HANDLERS ====================

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, step: PipelineStep) => {
    setDraggedStep(step);
    e.dataTransfer.effectAllowed = 'move';
    // Add a semi-transparent effect
    if (e.currentTarget) {
      e.currentTarget.style.opacity = '0.5';
    }
  };

  const handleDragEnd = (e: React.DragEvent<HTMLDivElement>) => {
    setDraggedStep(null);
    setDraggedOverStep(null);
    // Reset opacity
    if (e.currentTarget) {
      e.currentTarget.style.opacity = '1';
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>, step: PipelineStep) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    if (draggedStep && draggedStep.id !== step.id) {
      setDraggedOverStep(step);
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>, targetStep: PipelineStep) => {
    e.preventDefault();

    if (!draggedStep || draggedStep.id === targetStep.id) {
      return;
    }

    // Get the current displayed steps for this tab
    const displayedSteps = getDisplayedSteps();

    // Find indices
    const draggedIndex = displayedSteps.findIndex(s => s.id === draggedStep.id);
    const targetIndex = displayedSteps.findIndex(s => s.id === targetStep.id);

    if (draggedIndex === -1 || targetIndex === -1) {
      return;
    }

    // Create new array with reordered steps
    const reorderedSteps = [...displayedSteps];
    reorderedSteps.splice(draggedIndex, 1);
    reorderedSteps.splice(targetIndex, 0, draggedStep);

    // Extract step IDs in new order
    const newOrderIds = reorderedSteps.map(s => s.id);

    try {
      // Optimistically update local state first
      // Update the order values in the reordered steps
      const updatedReorderedSteps = reorderedSteps.map((step, index) => ({
        ...step,
        order: index + 1,
      }));

      // Update the global steps array by replacing the affected steps
      const otherSteps = steps.filter(s => !newOrderIds.includes(s.id));
      const newSteps = [...otherSteps, ...updatedReorderedSteps].sort((a, b) => a.order - b.order);
      setSteps(newSteps);

      // Call API to persist the change (no await needed for UI responsiveness)
      pipelineApi.reorderSteps(newOrderIds).catch(err => {
        // If API fails, reload to get correct state
        setError((err as Error).message);
        loadSteps();
      });

      setSuccess('Schritte erfolgreich neu geordnet!');
      setTimeout(() => setSuccess(''), 2000);
    } catch (err) {
      setError((err as Error).message);
      // Reload on error to restore correct state
      await loadSteps();
    } finally {
      setDraggedStep(null);
      setDraggedOverStep(null);
    }
  };

  // ==================== RENDER HELPERS ====================

  const getEngineIcon = (engine: string) => {
    switch (engine) {
      case 'PADDLEOCR':
        return <Brain className="w-5 h-5" />;
      case 'VISION_LLM':
        return <ImageIcon className="w-5 h-5" />;
      case 'HYBRID':
        return <Boxes className="w-5 h-5" />;
      case 'MISTRAL_OCR':
        return <Sparkles className="w-5 h-5" />;
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
            {engines &&
              Object.entries(engines).map(([engineKey, engineInfo]) => {
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

        {/* PII Removal Toggle */}
        <div className="mt-6 pt-6 border-t border-primary-200">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h4 className="font-semibold text-primary-900 mb-1 flex items-center space-x-2">
                <Shield className="w-4 h-4 text-brand-600" />
                <span>PII-Entfernung nach OCR</span>
              </h4>
              <p className="text-sm text-primary-600">
                Entfernt automatisch personenbezogene Daten (Namen, Adressen, etc.) nach der
                Texterkennung - lokal und datenschutzkonform
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={piiRemovalEnabled}
                onChange={e => setPiiRemovalEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-neutral-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-brand-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
              <span className="ml-3 text-sm font-medium text-primary-700">
                {piiRemovalEnabled ? 'Aktiviert' : 'Deaktiviert'}
              </span>
            </label>
          </div>
        </div>

        {/* Guidelines Analysis Toggle */}
        <div className="mt-6 pt-6 border-t border-primary-200">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h4 className="font-semibold text-primary-900 mb-1 flex items-center space-x-2">
                <BookOpen className="w-4 h-4 text-brand-600" />
                <span>Leitlinien-Analyse (AWMF)</span>
              </h4>
              <p className="text-sm text-primary-600">
                Zeigt automatisch relevante AWMF-Leitlinienempfehlungen nach der Übersetzung an
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={guidelinesEnabled}
                onChange={e => setGuidelinesEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-neutral-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-brand-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-neutral-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-600"></div>
              <span className="ml-3 text-sm font-medium text-primary-700">
                {guidelinesEnabled ? 'Aktiviert' : 'Deaktiviert'}
              </span>
            </label>
          </div>
        </div>
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
          <div className="flex items-center space-x-2">
            <button
              onClick={async () => {
                await loadDocumentClasses();
                setSuccess('Dokumentklassen aktualisiert!');
                setTimeout(() => setSuccess(''), 2000);
              }}
              disabled={classesLoading}
              className="p-2 hover:bg-primary-100 rounded-lg transition-colors text-primary-600"
              title="Dokumentklassen aktualisieren"
            >
              <RefreshCw className={`w-4 h-4 ${classesLoading ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={handleAddStep} className="btn-primary flex items-center space-x-2">
              <Plus className="w-4 h-4" />
              <span>Schritt hinzufügen</span>
            </button>
          </div>
        </div>

        {/* Pipeline Context Tabs */}
        <div className="border-b border-primary-200 -mx-6 px-6 mb-6">
          <div className="flex space-x-1 -mb-px overflow-x-auto">
            {/* Pre-Branching Tab */}
            <button
              onClick={() => setActivePipelineTab('pre-branching')}
              className={`flex items-center space-x-2 px-6 py-3 rounded-t-lg font-medium transition-all whitespace-nowrap ${
                activePipelineTab === 'pre-branching'
                  ? 'bg-white border-t-2 border-x-2 border-brand-600 text-brand-700 -mb-px'
                  : 'text-primary-600 hover:bg-primary-50 border-b-2 border-transparent'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Pre-Branching</span>
              <span
                className={`px-2 py-0.5 text-xs rounded ${
                  activePipelineTab === 'pre-branching'
                    ? 'bg-brand-100 text-brand-700'
                    : 'bg-primary-100 text-primary-600'
                }`}
              >
                {getStepCount('pre-branching')}
              </span>
            </button>

            {/* Dynamic Document Class Tabs */}
            {documentClasses.map(docClass => (
              <button
                key={docClass.id}
                onClick={() => setActivePipelineTab(docClass.id)}
                className={`flex items-center space-x-2 px-6 py-3 rounded-t-lg font-medium transition-all whitespace-nowrap ${
                  activePipelineTab === docClass.id
                    ? 'bg-white border-t-2 border-x-2 border-brand-600 text-brand-700 -mb-px'
                    : 'text-primary-600 hover:bg-primary-50 border-b-2 border-transparent'
                }`}
              >
                <span className="text-xl">{docClass.icon}</span>
                <span>{docClass.display_name}</span>
                <span
                  className={`px-2 py-0.5 text-xs rounded ${
                    activePipelineTab === docClass.id
                      ? 'bg-brand-100 text-brand-700'
                      : 'bg-primary-100 text-primary-600'
                  }`}
                >
                  {getStepCount(docClass.id)}
                </span>
              </button>
            ))}

            {/* Post-Branching Tab */}
            <button
              onClick={() => setActivePipelineTab('post-branching')}
              className={`flex items-center space-x-2 px-6 py-3 rounded-t-lg font-medium transition-all whitespace-nowrap ${
                activePipelineTab === 'post-branching'
                  ? 'bg-white border-t-2 border-x-2 border-brand-600 text-brand-700 -mb-px'
                  : 'text-primary-600 hover:bg-primary-50 border-b-2 border-transparent'
              }`}
            >
              <Boxes className="w-4 h-4" />
              <span>Post-Branching</span>
              <span
                className={`px-2 py-0.5 text-xs rounded ${
                  activePipelineTab === 'post-branching'
                    ? 'bg-brand-100 text-brand-700'
                    : 'bg-primary-100 text-primary-600'
                }`}
              >
                {getStepCount('post-branching')}
              </span>
            </button>
          </div>
        </div>

        {stepsLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
          </div>
        ) : getDisplayedSteps().length === 0 ? (
          <div className="text-center py-8 text-primary-500">
            {activePipelineTab === 'pre-branching' ? (
              <>
                <p>Keine Pre-Branching Schritte konfiguriert.</p>
                <p className="text-sm mt-2">
                  Diese Schritte laufen VOR der dokumentspezifischen Verarbeitung.
                </p>
                <p className="text-sm">
                  Klicken Sie auf &quot;Schritt hinzufügen&quot;, um zu beginnen.
                </p>
              </>
            ) : activePipelineTab === 'post-branching' ? (
              <>
                <p>Keine Post-Branching Schritte konfiguriert.</p>
                <p className="text-sm mt-2">
                  Diese Schritte laufen NACH der dokumentspezifischen Verarbeitung.
                </p>
                <p className="text-sm">
                  Ideal für universelle Aufgaben wie Übersetzung oder Formatierung.
                </p>
              </>
            ) : (
              <>
                <p>Keine Schritte für {getDocumentClassName(activePipelineTab)} konfiguriert.</p>
                <p className="text-sm mt-2">
                  Klicken Sie auf &quot;Schritt hinzufügen&quot;, um klassenspezifische Verarbeitung
                  zu erstellen.
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {getDisplayedSteps().map(step => {
              const isExpanded = expandedSteps.has(step.id);

              return (
                <div
                  key={step.id}
                  draggable={true}
                  onDragStart={e => handleDragStart(e, step)}
                  onDragEnd={handleDragEnd}
                  onDragOver={e => handleDragOver(e, step)}
                  onDrop={e => handleDrop(e, step)}
                  className={`border rounded-lg transition-all cursor-grab active:cursor-grabbing ${
                    draggedOverStep?.id === step.id
                      ? 'border-brand-500 border-2 bg-brand-50 shadow-lg scale-105'
                      : step.is_branching_step
                        ? 'border-orange-300 bg-gradient-to-r from-amber-50/50 to-orange-50/50 shadow-md'
                        : step.enabled
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
                        <div
                          className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                            step.enabled
                              ? 'bg-brand-100 text-brand-700'
                              : 'bg-neutral-200 text-neutral-600'
                          }`}
                        >
                          {step.order}
                        </div>

                        <div>
                          <div className="flex items-center space-x-2 flex-wrap">
                            <h4
                              className={`font-semibold ${step.enabled ? 'text-primary-900' : 'text-neutral-600'}`}
                            >
                              {step.name}
                            </h4>
                            {!step.enabled && (
                              <span className="text-xs px-2 py-1 bg-neutral-200 text-neutral-600 rounded">
                                Deaktiviert
                              </span>
                            )}
                            {/* Branching Point Indicator */}
                            {step.is_branching_step && (
                              <span className="text-xs px-2 py-1 bg-gradient-to-r from-amber-100 to-orange-100 text-orange-700 border border-orange-300 rounded flex items-center space-x-1 font-semibold">
                                <Zap className="w-3 h-3" />
                                <span>VERZWEIGUNG</span>
                              </span>
                            )}
                            {/* Document Class Label (if different from active tab) */}
                            {step.document_class_id !== null &&
                              step.document_class_id !== activePipelineTab && (
                                <span className="text-xs px-2 py-1 bg-brand-100 text-brand-700 border border-brand-300 rounded">
                                  {getDocumentClassName(step.document_class_id)}
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
                        title={isExpanded ? 'Einklappen' : 'Aufklappen'}
                      >
                        {isExpanded ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>

                      {/* Toggle Switch for Enable/Disable */}
                      <button
                        onClick={() => handleToggleStep(step)}
                        className="relative inline-flex items-center"
                        title={step.enabled ? 'Schritt deaktivieren' : 'Schritt aktivieren'}
                      >
                        <div
                          className={`w-11 h-6 rounded-full transition-colors ${
                            step.enabled ? 'bg-success-500' : 'bg-neutral-300'
                          }`}
                        >
                          <div
                            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow-md transition-transform ${
                              step.enabled ? 'translate-x-5' : 'translate-x-0'
                            }`}
                          />
                        </div>
                      </button>

                      <button
                        onClick={() => handleEditStep(step)}
                        className="p-2 hover:bg-brand-100 rounded-lg transition-colors text-brand-600"
                        title={t('common.edit', 'Bearbeiten')}
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => handleOpenDuplicateModal(step)}
                        className="p-2 hover:bg-brand-100 rounded-lg transition-colors text-brand-600"
                        title={t('pipeline.duplicateStep', 'Schritt duplizieren')}
                      >
                        <Copy className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => handleDeleteStep(step.id)}
                        className="p-2 hover:bg-error-100 rounded-lg transition-colors text-error-600"
                        title={t('common.delete', 'Löschen')}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {isExpanded && (
                    <div className="border-t border-primary-200 p-4 bg-neutral-50 space-y-3">
                      {step.system_prompt && (
                        <div>
                          <h5 className="font-semibold text-sm text-primary-900 mb-2">
                            System-Prompt:
                          </h5>
                          <pre className="text-xs bg-blue-50 border border-blue-200 rounded p-3 overflow-x-auto whitespace-pre-wrap text-primary-700">
                            {step.system_prompt}
                          </pre>
                        </div>
                      )}
                      <div>
                        <h5 className="font-semibold text-sm text-primary-900 mb-2">
                          Prompt Template:
                        </h5>
                        <pre className="text-xs bg-white border border-primary-200 rounded p-3 overflow-x-auto whitespace-pre-wrap text-primary-700">
                          {step.prompt_template}
                        </pre>
                      </div>
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
          documentClasses={documentClasses}
          defaultDocumentClassId={getDefaultDocumentClassId()}
          defaultPostBranching={getDefaultPostBranching()}
          pipelineContext={getDocumentClassName(activePipelineTab)}
          isOpen={isEditorOpen}
          onClose={() => {
            setIsEditorOpen(false);
            setEditingStep(null);
          }}
          onSave={async () => {
            setIsEditorOpen(false);
            setEditingStep(null);
            await loadSteps();
            await loadDocumentClasses(); // Refresh in case new class was created
            setSuccess('Schritt erfolgreich gespeichert!');
            setTimeout(() => setSuccess(''), 3000);
          }}
        />
      )}

      {/* Duplicate Step Modal */}
      {isDuplicateModalOpen && stepToDuplicate && (
        <DuplicateStepModal
          isOpen={isDuplicateModalOpen}
          onClose={() => {
            setIsDuplicateModalOpen(false);
            setStepToDuplicate(null);
          }}
          originalStep={stepToDuplicate}
          onDuplicate={handleDuplicateStep}
        />
      )}
    </div>
  );
};

export default PipelineBuilder;
