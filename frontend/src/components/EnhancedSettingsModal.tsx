import React, { useState, useEffect } from 'react';
import { X, Settings, Save, RotateCcw, TestTube, Download, Upload, Eye, EyeOff, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import settingsService from '../services/settings';
import { DocumentClass, DocumentPrompts, DocumentTypeInfo, PROMPT_STEPS, GLOBAL_PROMPT_STEPS, PipelineSettings, PipelineStatsResponse, GlobalPrompts, GlobalPromptsResponse, OCRSettings } from '../types/settings';

interface EnhancedSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EnhancedSettingsModal: React.FC<EnhancedSettingsModalProps> = ({ isOpen, onClose }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [authError, setAuthError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Document types and prompts
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeInfo[]>([]);
  const [selectedDocumentType, setSelectedDocumentType] = useState<DocumentClass>(DocumentClass.ARZTBRIEF);
  const [prompts, setPrompts] = useState<DocumentPrompts | null>(null);
  const [promptsLoading, setPromptsLoading] = useState(false);
  const [promptsError, setPromptsError] = useState('');

  // Prompt editing
  const [editingPrompt, setEditingPrompt] = useState<string | null>(null);
  const [editedPrompts, setEditedPrompts] = useState<DocumentPrompts | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Prompt testing
  const [testingPrompt, setTestingPrompt] = useState<string | null>(null);
  const [testSample, setTestSample] = useState('');
  const [testResult, setTestResult] = useState('');
  const [testLoading, setTestLoading] = useState(false);
  const [testError, setTestError] = useState('');

  // Show/hide passwords
  const [showPasswords, setShowPasswords] = useState(false);

  // Pipeline optimization settings
  const [pipelineSettings, setPipelineSettings] = useState<PipelineSettings | null>(null);
  const [pipelineStats, setPipelineStats] = useState<PipelineStatsResponse | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsError, setSettingsError] = useState('');
  const [updatingSettings, setUpdatingSettings] = useState(false);

  // Active tab for settings
  const [activeTab, setActiveTab] = useState<'prompts' | 'global' | 'ocr' | 'optimization' | 'statistics'>('prompts');

  // Global prompts state
  const [globalPrompts, setGlobalPrompts] = useState<GlobalPrompts | null>(null);
  const [editedGlobalPrompts, setEditedGlobalPrompts] = useState<GlobalPrompts | null>(null);
  const [globalPromptsLoading, setGlobalPromptsLoading] = useState(false);
  const [globalPromptsError, setGlobalPromptsError] = useState('');
  const [savingGlobal, setSavingGlobal] = useState(false);
  const [globalSaveError, setGlobalSaveError] = useState('');
  const [globalSaveSuccess, setGlobalSaveSuccess] = useState(false);

  // Model configuration state
  const [modelConfig, setModelConfig] = useState<{
    model_mapping: Record<string, string>;
    environment_config: Record<string, string>;
    model_descriptions: Record<string, string>;
  } | null>(null);

  // OCR settings state
  const [ocrSettings, setOcrSettings] = useState<OCRSettings | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState('');
  const [ocrSaving, setOcrSaving] = useState(false);

  // Check authentication on mount only if we have a token
  useEffect(() => {
    if (isOpen && settingsService.isAuthenticated()) {
      checkAuth();
    }
  }, [isOpen]);

  // Load document types when authenticated
  useEffect(() => {
    if (isAuthenticated && documentTypes.length === 0) {
      loadDocumentTypes();
    }
  }, [isAuthenticated]);

  // Load prompts when document type changes
  useEffect(() => {
    if (isAuthenticated && selectedDocumentType && activeTab === 'prompts') {
      loadPrompts();
    }
  }, [selectedDocumentType, isAuthenticated, activeTab]);

  // Load pipeline settings and stats when authenticated
  useEffect(() => {
    if (isAuthenticated && activeTab === 'optimization') {
      loadPipelineSettings();
      loadPipelineStats();
    }
  }, [isAuthenticated, activeTab]);

  // Load pipeline stats for statistics tab
  useEffect(() => {
    if (isAuthenticated && activeTab === 'statistics') {
      loadPipelineStats();
    }
  }, [isAuthenticated, activeTab]);

  // Load global prompts when authenticated
  useEffect(() => {
    if (isAuthenticated && activeTab === 'global') {
      loadGlobalPrompts();
    }
  }, [isAuthenticated, activeTab]);

  // Load model configuration when authenticated
  useEffect(() => {
    if (isAuthenticated && !modelConfig) {
      loadModelConfiguration();
    }
  }, [isAuthenticated]);

  // Load OCR settings when authenticated
  useEffect(() => {
    if (isAuthenticated && activeTab === 'ocr') {
      loadOCRSettings();
    }
  }, [isAuthenticated, activeTab]);

  const checkAuth = async () => {
    try {
      const authenticated = await settingsService.checkAuth();
      setIsAuthenticated(authenticated);
      if (authenticated) {
        setAuthError('');
      }
    } catch (error) {
      setIsAuthenticated(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setAuthError('');

    try {
      const response = await settingsService.authenticate(accessCode);
      if (response.success) {
        setIsAuthenticated(true);
        setAccessCode('');
      }
    } catch (error: any) {
      setAuthError(error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocumentTypes = async () => {
    try {
      const types = await settingsService.getDocumentTypes();
      setDocumentTypes(types);
    } catch (error) {
      console.error('Failed to load document types:', error);
    }
  };

  const loadPrompts = async () => {
    setPromptsLoading(true);
    setPromptsError('');

    try {
      const response = await settingsService.getPrompts(selectedDocumentType);
      setPrompts(response.prompts);
      setEditedPrompts(response.prompts);
    } catch (error: any) {
      setPromptsError(error.message);
    } finally {
      setPromptsLoading(false);
    }
  };

  const handlePromptChange = (field: keyof DocumentPrompts, value: string) => {
    if (editedPrompts) {
      setEditedPrompts({
        ...editedPrompts,
        [field]: value,
        // Preserve metadata fields
        document_type: selectedDocumentType,
        version: editedPrompts.version || 1,
        last_modified: editedPrompts.last_modified || new Date().toISOString(),
        modified_by: editedPrompts.modified_by || 'admin'
      });
    }
  };

  const handleSavePrompts = async () => {
    if (!editedPrompts) return;

    setSaving(true);
    setSaveError('');
    setSaveSuccess(false);

    try {
      // Ensure we include all required fields for the backend
      const promptsToSave: DocumentPrompts = {
        ...editedPrompts,
        document_type: selectedDocumentType,
        version: editedPrompts.version || 1,
        last_modified: new Date().toISOString(),
        modified_by: 'admin'
      };

      await settingsService.updatePrompts(selectedDocumentType, promptsToSave, 'admin');
      setPrompts(promptsToSave);
      setEditedPrompts(promptsToSave);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error: any) {
      setSaveError(error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleResetPrompts = async () => {
    if (!window.confirm('Möchten Sie die Prompts wirklich auf die Standardwerte zurücksetzen?')) {
      return;
    }

    setSaving(true);
    setSaveError('');

    try {
      await settingsService.resetPrompts(selectedDocumentType);
      await loadPrompts(); // Reload prompts
    } catch (error: any) {
      setSaveError(error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleTestPrompt = async (field: keyof DocumentPrompts) => {
    if (!editedPrompts || !testSample.trim()) {
      setTestError('Bitte geben Sie einen Testtext ein');
      return;
    }

    // Only test string prompt fields, not metadata fields
    const promptFields = ['medical_validation_prompt', 'classification_prompt', 'preprocessing_prompt', 'translation_prompt', 'fact_check_prompt', 'grammar_check_prompt', 'language_translation_prompt', 'final_check_prompt', 'formatting_prompt'];
    if (!promptFields.includes(field)) {
      setTestError('Dieses Feld kann nicht getestet werden');
      return;
    }

    setTestingPrompt(field);
    setTestLoading(true);
    setTestError('');
    setTestResult('');

    try {
      const response = await settingsService.testPrompt({
        prompt: (editedPrompts[field] as string) || '',
        sample_text: testSample,
        temperature: 0.3,
        max_tokens: 1000
      });

      setTestResult(response.result);
    } catch (error: any) {
      setTestError(error.message);
    } finally {
      setTestLoading(false);
      setTestingPrompt(null);
    }
  };

  const handleExport = async () => {
    try {
      const exportData = await settingsService.exportPrompts();
      settingsService.downloadExport(exportData, `prompts_export_${new Date().toISOString().split('T')[0]}.json`);
    } catch (error: any) {
      console.error('Export failed:', error);
    }
  };

  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    settingsService.readImportFile(file)
      .then(async (data) => {
        try {
          await settingsService.importPrompts(data);
          await loadPrompts(); // Reload current prompts
          alert('Prompts erfolgreich importiert!');
        } catch (error: any) {
          alert(`Import fehlgeschlagen: ${error.message}`);
        }
      })
      .catch((error) => {
        alert(`Datei konnte nicht gelesen werden: ${error.message}`);
      });

    // Reset file input
    event.target.value = '';
  };

  // Pipeline optimization methods
  const loadPipelineSettings = async () => {
    setSettingsLoading(true);
    setSettingsError('');

    try {
      const settings = await settingsService.getPipelineSettings();
      setPipelineSettings(settings);
    } catch (error: any) {
      setSettingsError(error.message);
    } finally {
      setSettingsLoading(false);
    }
  };

  const loadPipelineStats = async () => {
    try {
      const stats = await settingsService.getPipelineStats();
      setPipelineStats(stats);
    } catch (error: any) {
      console.error('Failed to load pipeline stats:', error);
      setPipelineStats(null);
      // If it's an authentication error, we might want to handle it differently
      if (error.message?.includes('401') || error.message?.includes('Authentication')) {
        console.warn('Pipeline stats authentication failed - user may need to re-login');
      }
    }
  };

  const handleSettingsUpdate = async (key: keyof PipelineSettings, value: any) => {
    if (!pipelineSettings) return;

    setUpdatingSettings(true);

    try {
      const response = await settingsService.updatePipelineSettings({ [key]: value });
      setPipelineSettings(response.settings);

      // Show success message
      if (response.warning) {
        alert(`Einstellungen aktualisiert! ${response.warning}`);
      }
    } catch (error: any) {
      console.error('Failed to update settings:', error);
      alert(`Fehler beim Aktualisieren: ${error.message}`);
    } finally {
      setUpdatingSettings(false);
    }
  };

  const handleClearCache = async () => {
    try {
      await settingsService.clearPipelineCache();
      await loadPipelineStats(); // Refresh stats
      alert('Pipeline-Cache erfolgreich geleert!');
    } catch (error: any) {
      alert(`Fehler beim Cache-Leeren: ${error.message}`);
    }
  };

  // Global prompts methods
  const loadGlobalPrompts = async () => {
    setGlobalPromptsLoading(true);
    setGlobalPromptsError('');

    try {
      const response = await settingsService.getGlobalPrompts();
      setGlobalPrompts(response.global_prompts);
      setEditedGlobalPrompts(response.global_prompts);
    } catch (error: any) {
      setGlobalPromptsError(error.message);
    } finally {
      setGlobalPromptsLoading(false);
    }
  };

  const handleGlobalPromptChange = (field: keyof GlobalPrompts, value: string) => {
    if (editedGlobalPrompts) {
      setEditedGlobalPrompts({
        ...editedGlobalPrompts,
        [field]: value
      });
    }
  };

  const handleSaveGlobalPrompts = async () => {
    if (!editedGlobalPrompts) return;

    setSavingGlobal(true);
    setGlobalSaveError('');
    setGlobalSaveSuccess(false);

    try {
      await settingsService.updateGlobalPrompts({
        ...editedGlobalPrompts,
        user: 'admin'
      });

      setGlobalPrompts(editedGlobalPrompts);
      setGlobalSaveSuccess(true);
      setTimeout(() => setGlobalSaveSuccess(false), 3000);
    } catch (error: any) {
      setGlobalSaveError(error.message);
    } finally {
      setSavingGlobal(false);
    }
  };

  const handleResetGlobalPrompts = async () => {
    if (!window.confirm('Möchten Sie die globalen Prompts wirklich auf die Standardwerte zurücksetzen?')) {
      return;
    }

    setSavingGlobal(true);
    setGlobalSaveError('');

    try {
      await settingsService.resetGlobalPrompts();
      await loadGlobalPrompts(); // Reload prompts
    } catch (error: any) {
      setGlobalSaveError(error.message);
    } finally {
      setSavingGlobal(false);
    }
  };

  const handleTestGlobalPrompt = async (field: keyof GlobalPrompts) => {
    if (!editedGlobalPrompts || !testSample.trim()) {
      setTestError('Bitte geben Sie einen Testtext ein');
      return;
    }

    setTestingPrompt(field);
    setTestLoading(true);
    setTestError('');
    setTestResult('');

    try {
      const response = await settingsService.testGlobalPrompt({
        prompt: editedGlobalPrompts[field] || '',
        sample_text: testSample,
        temperature: 0.3,
        max_tokens: 1000
      });

      setTestResult(response.result);
    } catch (error: any) {
      setTestError(error.message);
    } finally {
      setTestLoading(false);
      setTestingPrompt(null);
    }
  };

  const handleExportGlobal = async () => {
    try {
      const exportData = await settingsService.exportGlobalPrompts();
      settingsService.downloadExport(exportData, `global_prompts_export_${new Date().toISOString().split('T')[0]}.json`);
    } catch (error: any) {
      console.error('Global prompts export failed:', error);
    }
  };

  const handleImportGlobal = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    settingsService.readImportFile(file)
      .then(async (data) => {
        try {
          await settingsService.importGlobalPrompts(data);
          await loadGlobalPrompts(); // Reload prompts
          alert('Globale Prompts erfolgreich importiert!');
        } catch (error: any) {
          alert(`Import fehlgeschlagen: ${error.message}`);
        }
      })
      .catch((error) => {
        alert(`Datei konnte nicht gelesen werden: ${error.message}`);
      });

    // Reset file input
    event.target.value = '';
  };

  // Model configuration methods
  const loadModelConfiguration = async () => {
    try {
      const config = await settingsService.getModelConfiguration();
      setModelConfig(config);
    } catch (error: any) {
      console.error('Failed to load model configuration:', error);
    }
  };

  // OCR settings methods
  const loadOCRSettings = async () => {
    setOcrLoading(true);
    setOcrError('');

    try {
      const settings = await settingsService.getOCRSettings();
      setOcrSettings(settings);
    } catch (error: any) {
      setOcrError(error.message);
    } finally {
      setOcrLoading(false);
    }
  };

  const handleOCRSettingsUpdate = async (key: keyof OCRSettings, value: any) => {
    if (!ocrSettings) return;

    setOcrSaving(true);

    try {
      const response = await settingsService.updateOCRSettings({ [key]: value });

      // Reload the settings to get the updated values
      await loadOCRSettings();

      // Show success message
      if (response.message) {
        alert(`OCR-Einstellungen aktualisiert! ${response.message}`);
      }
    } catch (error: any) {
      console.error('Failed to update OCR settings:', error);
      alert(`Fehler beim Aktualisieren: ${error.message}`);
    } finally {
      setOcrSaving(false);
    }
  };

  // Helper function to get model name for a prompt
  const getModelForPrompt = (promptKey: string): string => {
    if (!modelConfig) return 'Loading...';
    const model = modelConfig.model_mapping[promptKey];
    return model || 'Unknown';
  };

  // Helper function to format model name for display
  const formatModelName = (modelName: string): string => {
    if (modelName === 'Loading...' || modelName === 'Unknown') return modelName;

    // Dynamic model name formatting for better display

    // Llama variants
    if (modelName.includes('Meta-Llama-3_3-70B-Instruct')) return 'Llama 3.3 70B (Quality)';
    if (modelName.includes('Meta-Llama-3_3')) return 'Llama 3.3 (Quality)';
    if (modelName.includes('Meta-Llama') || modelName.includes('llama')) return 'Llama (Quality)';

    // Mistral variants
    if (modelName.includes('Mistral-Nemo-Instruct-2407')) return 'Mistral Nemo (Fast)';
    if (modelName.includes('Mistral-Nemo')) return 'Mistral Nemo (Fast)';
    if (modelName.includes('Mixtral-8x7B')) return 'Mixtral 8x7B (Quality)';
    if (modelName.includes('Mixtral-8x22B')) return 'Mixtral 8x22B (Quality)';
    if (modelName.includes('Mixtral')) return 'Mixtral (Quality)';
    if (modelName.includes('Mistral') || modelName.includes('mistral')) return 'Mistral (Fast)';

    // Qwen variants
    if (modelName.includes('Qwen2.5-VL-72B-Instruct')) return 'Qwen 2.5 VL 72B (Vision)';
    if (modelName.includes('Qwen2.5-VL')) return 'Qwen 2.5 VL (Vision)';
    if (modelName.includes('Qwen2.5-72B')) return 'Qwen 2.5 72B (Quality)';
    if (modelName.includes('Qwen2.5')) return 'Qwen 2.5 (Quality)';
    if (modelName.includes('Qwen') || modelName.includes('qwen')) return 'Qwen (Quality)';

    // Extract and format unknown models nicely
    const cleanName = modelName
      .replace(/[-_]/g, ' ')
      .replace(/\b\d+B\b/g, (match) => `${match} (Quality)`)
      .replace(/\bInstruct\b/i, '')
      .replace(/\bChat\b/i, '')
      .trim();

    // Return shortened version if too long
    return cleanName.length > 30 ? cleanName.substring(0, 27) + '...' : cleanName;
  };

  // Helper function to get badge color based on model type
  const getModelBadgeClass = (modelName: string): string => {
    // Fast models - green
    if (modelName.includes('Mistral-Nemo') || modelName.includes('mistral')) {
      return 'bg-green-100 text-green-800';
    }

    // Vision models - blue
    if (modelName.includes('VL') || modelName.includes('vision') || modelName.includes('Vision')) {
      return 'bg-blue-100 text-blue-800';
    }

    // Quality models - purple
    if (modelName.includes('Meta-Llama') || modelName.includes('llama') ||
        modelName.includes('Mixtral') || modelName.includes('70B') ||
        modelName.includes('72B') || modelName.includes('Qwen')) {
      return 'bg-purple-100 text-purple-800';
    }

    // Default - gray
    return 'bg-gray-100 text-gray-800';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-start justify-start p-2">
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative w-full max-w-none bg-white rounded-2xl shadow-2xl border border-primary-200 max-h-[95vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-primary-200 bg-gradient-to-r from-brand-50 to-accent-50">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center">
                <Settings className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-primary-900">Erweiterte Einstellungen</h2>
                <p className="text-sm text-primary-600">Verwalten Sie Prompts und Pipeline-Optimierungen</p>
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
          <div className="flex h-[calc(90vh-120px)]">
            {/* Left Sidebar - Navigation */}
            <div className="w-80 border-r border-primary-200 bg-neutral-50 p-6 overflow-y-auto">
              {!isAuthenticated ? (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-primary-900">Anmeldung</h3>
                  <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-primary-700 mb-2">
                        Zugangscode
                      </label>
                      <div className="relative">
                        <input
                          type={showPasswords ? 'text' : 'password'}
                          value={accessCode}
                          onChange={(e) => setAccessCode(e.target.value)}
                          className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                          placeholder="Zugangscode eingeben"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPasswords(!showPasswords)}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-primary-400 hover:text-primary-600"
                        >
                          {showPasswords ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {authError && (
                      <div className="flex items-center space-x-2 text-error-600 text-sm">
                        <AlertCircle className="w-4 h-4" />
                        <span>{authError}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={isLoading || !accessCode.trim()}
                      className="w-full btn-primary disabled:opacity-50"
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        'Anmelden'
                      )}
                    </button>
                  </form>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Tab Navigation */}
                  <div className="space-y-3">
                    <h3 className="text-lg font-semibold text-primary-900">Einstellungen</h3>
                    <div className="space-y-1">
                      <button
                        onClick={() => setActiveTab('prompts')}
                        className={`w-full text-left p-3 rounded-lg transition-all ${
                          activeTab === 'prompts'
                            ? 'bg-brand-100 text-brand-900 border border-brand-300'
                            : 'hover:bg-primary-100 text-primary-700'
                        }`}
                      >
                        📝 Prompt-Verwaltung
                      </button>
                      <button
                        onClick={() => setActiveTab('global')}
                        className={`w-full text-left p-3 rounded-lg transition-all ${
                          activeTab === 'global'
                            ? 'bg-brand-100 text-brand-900 border border-brand-300'
                            : 'hover:bg-primary-100 text-primary-700'
                        }`}
                      >
                        🌐 Globale Prompts
                      </button>
                      <button
                        onClick={() => setActiveTab('ocr')}
                        className={`w-full text-left p-3 rounded-lg transition-all ${
                          activeTab === 'ocr'
                            ? 'bg-brand-100 text-brand-900 border border-brand-300'
                            : 'hover:bg-primary-100 text-primary-700'
                        }`}
                      >
                        👁️ OCR-Einstellungen
                      </button>
                      <button
                        onClick={() => setActiveTab('optimization')}
                        className={`w-full text-left p-3 rounded-lg transition-all ${
                          activeTab === 'optimization'
                            ? 'bg-brand-100 text-brand-900 border border-brand-300'
                            : 'hover:bg-primary-100 text-primary-700'
                        }`}
                      >
                        🚀 Pipeline-Optimierung
                      </button>
                      <button
                        onClick={() => setActiveTab('statistics')}
                        className={`w-full text-left p-3 rounded-lg transition-all ${
                          activeTab === 'statistics'
                            ? 'bg-brand-100 text-brand-900 border border-brand-300'
                            : 'hover:bg-primary-100 text-primary-700'
                        }`}
                      >
                        📊 Statistiken
                      </button>
                    </div>
                  </div>

                  {/* Document Type Selection (only for prompts tab) */}
                  {activeTab === 'prompts' && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="font-semibold text-primary-900">Dokumenttypen</h4>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={handleExport}
                            className="p-2 text-primary-600 hover:bg-primary-100 rounded-lg transition-colors"
                            title="Exportieren"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <label className="p-2 text-primary-600 hover:bg-primary-100 rounded-lg transition-colors cursor-pointer" title="Importieren">
                            <Upload className="w-4 h-4" />
                            <input
                              type="file"
                              accept=".json"
                              onChange={handleImport}
                              className="hidden"
                            />
                          </label>
                        </div>
                      </div>

                      <div className="space-y-2">
                        {documentTypes.map((type) => (
                          <button
                            key={type.id}
                            onClick={() => setSelectedDocumentType(type.id as DocumentClass)}
                            className={`w-full text-left p-3 rounded-lg border transition-all ${
                              selectedDocumentType === type.id
                                ? 'border-brand-300 bg-brand-50 text-brand-900'
                                : 'border-primary-200 bg-white hover:border-primary-300 hover:bg-primary-50'
                            }`}
                          >
                            <div className="flex items-center space-x-2">
                              <span className="text-lg">{type.icon}</span>
                              <div>
                                <div className="font-medium text-sm">{type.name}</div>
                                <div className="text-xs text-primary-600">{type.description}</div>
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Pipeline Stats (only for optimization tab) */}
                  {activeTab === 'optimization' && pipelineStats && (
                    <div className="bg-gradient-to-br from-brand-50 to-accent-50 p-4 rounded-lg">
                      <h4 className="font-semibold text-primary-900 mb-3">Pipeline Status</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span>Modus:</span>
                          <span className="font-medium capitalize">{pipelineStats.pipeline_mode || 'Unbekannt'}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Cache Einträge:</span>
                          <span className="font-medium">{pipelineStats.cache_statistics?.active_entries || 0}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Cache Timeout:</span>
                          <span className="font-medium">{pipelineStats.cache_statistics?.cache_timeout_seconds || 0}s</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Right Content - Dynamic Content */}
            <div className="flex-1 p-6 overflow-y-auto">
              {!isAuthenticated ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <Settings className="w-16 h-16 text-primary-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-primary-700 mb-2">Anmeldung erforderlich</h3>
                    <p className="text-primary-500">Bitte melden Sie sich an, um die Einstellungen zu verwalten.</p>
                  </div>
                </div>
              ) : activeTab === 'prompts' ? (
                promptsLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
                      <p className="text-primary-600">Prompts werden geladen...</p>
                    </div>
                  </div>
                ) : promptsError ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <AlertCircle className="w-16 h-16 text-error-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-error-700 mb-2">Fehler beim Laden</h3>
                      <p className="text-error-600">{promptsError}</p>
                      <button
                        onClick={loadPrompts}
                        className="mt-4 btn-primary"
                      >
                        Erneut versuchen
                      </button>
                    </div>
                  </div>
                ) : editedPrompts ? (
                  <div className="space-y-6">
                    {/* Header with Save/Reset */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-bold text-primary-900">
                          {documentTypes.find(t => t.id === selectedDocumentType)?.name} - Prompts
                        </h3>
                        <p className="text-sm text-primary-600">
                          Bearbeiten Sie die Prompts für diesen Dokumenttyp
                        </p>
                      </div>
                      <div className="flex items-center space-x-3">
                        <button
                          onClick={handleResetPrompts}
                          disabled={saving}
                          className="btn-secondary disabled:opacity-50"
                        >
                          <RotateCcw className="w-4 h-4" />
                          Zurücksetzen
                        </button>
                        <button
                          onClick={handleSavePrompts}
                          disabled={saving}
                          className="btn-primary disabled:opacity-50"
                        >
                          {saving ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Save className="w-4 h-4" />
                          )}
                          Speichern
                        </button>
                      </div>
                    </div>

                    {/* Status Messages */}
                    {saveSuccess && (
                      <div className="flex items-center space-x-2 p-3 bg-success-50 border border-success-200 rounded-lg">
                        <CheckCircle className="w-5 h-5 text-success-600" />
                        <span className="text-success-700">Prompts erfolgreich gespeichert!</span>
                      </div>
                    )}

                    {saveError && (
                      <div className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg">
                        <AlertCircle className="w-5 h-5 text-error-600" />
                        <span className="text-error-700">{saveError}</span>
                      </div>
                    )}

                    {/* Prompts Editor */}
                    <div className="space-y-6">
                      {Object.entries(PROMPT_STEPS).map(([key, step]) => {
                        // Only process string prompt fields
                        const promptKey = key as keyof Pick<DocumentPrompts,
                          'medical_validation_prompt' | 'classification_prompt' | 'preprocessing_prompt' | 'translation_prompt' |
                          'fact_check_prompt' | 'grammar_check_prompt' | 'language_translation_prompt' | 'final_check_prompt' | 'formatting_prompt'
                        >;

                        return (
                          <div key={key} className="border border-primary-200 rounded-xl p-6 bg-white">
                            <div className="flex items-center justify-between mb-4">
                              <div>
                                <div className="flex items-center space-x-3 mb-2">
                                  <h4 className="text-lg font-semibold text-primary-900">{step.name}</h4>
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getModelBadgeClass(getModelForPrompt(promptKey))}`}>
                                    🤖 {formatModelName(getModelForPrompt(promptKey))}
                                  </span>
                                </div>
                                <p className="text-sm text-primary-600">{step.description}</p>
                              </div>
                              <button
                                onClick={() => handleTestPrompt(promptKey)}
                                disabled={testLoading || !testSample.trim()}
                                className="btn-ghost disabled:opacity-50"
                              >
                                <TestTube className="w-4 h-4" />
                                Testen
                              </button>
                            </div>

                            <textarea
                              value={editedPrompts[promptKey] || ''}
                              onChange={(e) => handlePromptChange(promptKey, e.target.value)}
                              className="w-full h-32 p-3 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none resize-none font-mono text-sm"
                              placeholder={step.placeholder}
                            />
                          </div>
                        );
                      })}
                    </div>

                    {/* Test Section */}
                    <div className="border border-primary-200 rounded-xl p-6 bg-gradient-to-br from-accent-50 to-brand-50">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">Prompt-Test</h4>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-primary-700 mb-2">
                            Testtext eingeben
                          </label>
                          <textarea
                            value={testSample}
                            onChange={(e) => setTestSample(e.target.value)}
                            className="w-full h-24 p-3 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none resize-none"
                            placeholder="Geben Sie hier einen medizinischen Text ein, um die Prompts zu testen..."
                          />
                        </div>

                        {testResult && (
                          <div>
                            <label className="block text-sm font-medium text-primary-700 mb-2">
                              Testergebnis
                            </label>
                            <div className="p-4 bg-white border border-primary-200 rounded-lg">
                              <pre className="whitespace-pre-wrap text-sm text-primary-800">{testResult}</pre>
                            </div>
                          </div>
                        )}

                        {testError && (
                          <div className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg">
                            <AlertCircle className="w-4 h-4 text-error-600" />
                            <span className="text-error-700">{testError}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : null
              ) : activeTab === 'global' ? (
                globalPromptsLoading ? (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
                    <p className="text-primary-600">Globale Prompts werden geladen...</p>
                  </div>
                ) : globalPromptsError ? (
                  <div className="text-center py-12">
                    <AlertCircle className="w-16 h-16 text-error-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-error-700 mb-2">Fehler beim Laden</h3>
                    <p className="text-error-600 mb-4">{globalPromptsError}</p>
                    <button
                      onClick={loadGlobalPrompts}
                      className="btn-primary"
                    >
                      Erneut versuchen
                    </button>
                  </div>
                ) : editedGlobalPrompts ? (
                  <div className="space-y-6">
                    {/* Header with Save/Reset */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-bold text-primary-900">🌐 Globale Prompts</h3>
                        <p className="text-sm text-primary-600">
                          Diese Prompts werden für alle Dokumenttypen verwendet und steuern die Vorverarbeitung
                        </p>
                      </div>
                      <div className="flex items-center space-x-3">
                        <button
                          onClick={handleExportGlobal}
                          className="btn-ghost"
                          title="Globale Prompts exportieren"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <label className="btn-ghost cursor-pointer" title="Globale Prompts importieren">
                          <Upload className="w-4 h-4" />
                          <input
                            type="file"
                            accept=".json"
                            onChange={handleImportGlobal}
                            className="hidden"
                          />
                        </label>
                        <button
                          onClick={handleResetGlobalPrompts}
                          disabled={savingGlobal}
                          className="btn-secondary disabled:opacity-50"
                        >
                          <RotateCcw className="w-4 h-4" />
                          Zurücksetzen
                        </button>
                        <button
                          onClick={handleSaveGlobalPrompts}
                          disabled={savingGlobal}
                          className="btn-primary disabled:opacity-50"
                        >
                          {savingGlobal ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Save className="w-4 h-4" />
                          )}
                          Speichern
                        </button>
                      </div>
                    </div>

                    {/* Status Messages */}
                    {globalSaveSuccess && (
                      <div className="flex items-center space-x-2 p-3 bg-success-50 border border-success-200 rounded-lg">
                        <CheckCircle className="w-5 h-5 text-success-600" />
                        <span className="text-success-700">Globale Prompts erfolgreich gespeichert!</span>
                      </div>
                    )}

                    {globalSaveError && (
                      <div className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg">
                        <AlertCircle className="w-5 h-5 text-error-600" />
                        <span className="text-error-700">{globalSaveError}</span>
                      </div>
                    )}

                    {/* Info Box */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                      <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                          <span className="text-blue-600 text-sm">ℹ️</span>
                        </div>
                        <div>
                          <h4 className="font-semibold text-blue-900 mb-1">Globale Prompts</h4>
                          <p className="text-sm text-blue-800">
                            Diese Prompts werden für <strong>alle</strong> Dokumenttypen verwendet. Änderungen wirken sich auf die gesamte Pipeline aus:
                          </p>
                          <ul className="text-sm text-blue-700 mt-2 space-y-1">
                            <li>• <strong>Medizinische Validierung:</strong> Erkennt medizinische Inhalte</li>
                            <li>• <strong>Dokumentklassifizierung:</strong> Bestimmt den Dokumenttyp</li>
                            <li>• <strong>Datenbereinigung:</strong> Entfernt persönliche Informationen</li>
                            <li>• <strong>Grammatikprüfung:</strong> Korrigiert Sprache und Stil</li>
                            <li>• <strong>Sprachübersetzung:</strong> Template für Übersetzungen</li>
                          </ul>
                        </div>
                      </div>
                    </div>

                    {/* Global Prompts Editor */}
                    <div className="space-y-6">
                      {Object.entries(GLOBAL_PROMPT_STEPS).map(([key, step]) => {
                        const promptKey = key as keyof GlobalPrompts;

                        return (
                          <div key={key} className="border border-primary-200 rounded-xl p-6 bg-white">
                            <div className="flex items-center justify-between mb-4">
                              <div>
                                <div className="flex items-center space-x-3 mb-2">
                                  <h4 className="text-lg font-semibold text-primary-900">{step.name}</h4>
                                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getModelBadgeClass(getModelForPrompt(promptKey))}`}>
                                    🤖 {formatModelName(getModelForPrompt(promptKey))}
                                  </span>
                                </div>
                                <p className="text-sm text-primary-600">{step.description}</p>
                                <span className={`inline-block mt-2 px-2 py-1 rounded-full text-xs font-medium ${
                                  step.category === 'preprocessing' ? 'bg-blue-100 text-blue-800' :
                                  step.category === 'quality' ? 'bg-green-100 text-green-800' :
                                  step.category === 'translation' ? 'bg-purple-100 text-purple-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {step.category === 'preprocessing' ? 'Vorverarbeitung' :
                                   step.category === 'quality' ? 'Qualitätskontrolle' :
                                   step.category === 'translation' ? 'Übersetzung' : 'Sonstige'}
                                </span>
                              </div>
                              <button
                                onClick={() => handleTestGlobalPrompt(promptKey)}
                                disabled={testLoading || !testSample.trim()}
                                className="btn-ghost disabled:opacity-50"
                              >
                                <TestTube className="w-4 h-4" />
                                Testen
                              </button>
                            </div>

                            <textarea
                              value={editedGlobalPrompts[promptKey] || ''}
                              onChange={(e) => handleGlobalPromptChange(promptKey, e.target.value)}
                              className="w-full h-32 p-3 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none resize-none font-mono text-sm"
                              placeholder={step.placeholder}
                            />
                          </div>
                        );
                      })}
                    </div>

                    {/* Test Section for Global Prompts */}
                    <div className="border border-primary-200 rounded-xl p-6 bg-gradient-to-br from-accent-50 to-brand-50">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">🧪 Globale Prompt-Tests</h4>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-primary-700 mb-2">
                            Testtext eingeben
                          </label>
                          <textarea
                            value={testSample}
                            onChange={(e) => setTestSample(e.target.value)}
                            className="w-full h-24 p-3 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none resize-none"
                            placeholder="Geben Sie hier einen Text ein, um die globalen Prompts zu testen..."
                          />
                        </div>

                        {testResult && (
                          <div>
                            <label className="block text-sm font-medium text-primary-700 mb-2">
                              Testergebnis
                            </label>
                            <div className="p-4 bg-white border border-primary-200 rounded-lg">
                              <pre className="whitespace-pre-wrap text-sm text-primary-800">{testResult}</pre>
                            </div>
                          </div>
                        )}

                        {testError && (
                          <div className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg">
                            <AlertCircle className="w-4 h-4 text-error-600" />
                            <span className="text-error-700">{testError}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : null
              ) : activeTab === 'ocr' ? (
                ocrLoading ? (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
                    <p className="text-primary-600">OCR-Einstellungen werden geladen...</p>
                  </div>
                ) : ocrError ? (
                  <div className="text-center py-12">
                    <AlertCircle className="w-16 h-16 text-error-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-error-700 mb-2">Fehler beim Laden</h3>
                    <p className="text-error-600 mb-4">{ocrError}</p>
                    <button
                      onClick={loadOCRSettings}
                      className="btn-primary"
                    >
                      Erneut versuchen
                    </button>
                  </div>
                ) : ocrSettings ? (
                  <div className="space-y-6">
                    {/* Header */}
                    <div>
                      <h3 className="text-xl font-bold text-primary-900">👁️ OCR-Einstellungen</h3>
                      <p className="text-sm text-primary-600">
                        Konfigurieren Sie das Enhanced OCR System für optimale Texterkennung
                      </p>
                    </div>

                    {/* Info Box */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
                      <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                          <span className="text-blue-600 text-sm">ℹ️</span>
                        </div>
                        <div>
                          <h4 className="font-semibold text-blue-900 mb-1">Enhanced OCR System</h4>
                          <p className="text-sm text-blue-800">
                            Das System verwendet intelligente Strategien für optimale Texterkennung:
                          </p>
                          <ul className="text-sm text-blue-700 mt-2 space-y-1">
                            <li>• <strong>Bedingt (Empfohlen):</strong> Automatische Wahl zwischen lokaler und KI-basierter OCR basierend auf Bildqualität</li>
                            <li>• <strong>Nur Vision-KI:</strong> Ausschließlich Qwen 2.5 VL für alle Bilder und PDFs</li>
                            <li>• <strong>Nur lokal:</strong> Traditionelle OCR-Bibliotheken (Tesseract)</li>
                            <li>• <strong>Hybrid:</strong> Kombination aller verfügbaren Methoden mit Qualitätsprüfung</li>
                          </ul>
                          <div className="mt-3 p-2 bg-blue-100 rounded-lg">
                            <p className="text-sm text-blue-800">
                              <strong>💡 Intelligente Verarbeitung:</strong> OCR läuft nur bei Bildern/PDFs. Text-Dateien werden direkt verarbeitet.
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* OCR Strategy Settings */}
                    <div className="bg-white border border-primary-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">🎯 OCR-Strategie</h4>

                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-primary-700 mb-2">
                            Strategie auswählen
                          </label>
                          <select
                            value={ocrSettings.strategy}
                            onChange={(e) => handleOCRSettingsUpdate('strategy', e.target.value)}
                            disabled={ocrSaving}
                            className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none disabled:opacity-50"
                          >
                            <option value="conditional">🤖 Bedingt (Empfohlen)</option>
                            <option value="vision_only">👁️ Nur Vision-KI</option>
                            <option value="local_only">🖥️ Nur lokal</option>
                            <option value="hybrid">🔄 Hybrid</option>
                          </select>
                          <p className="text-xs text-primary-500 mt-1">
                            Die bedingte Strategie wählt automatisch die beste Methode basierend auf der Dokumentqualität
                          </p>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-primary-700 mb-2">
                            Vision-Modell: {ocrSettings.vision_model}
                          </label>
                          <div className="flex items-center space-x-2 text-sm text-success-700">
                            <CheckCircle className="w-4 h-4" />
                            <span>Qwen 2.5 VL 72B Instruct (OVH AI)</span>
                          </div>
                          <p className="text-xs text-primary-500 mt-1">
                            Hochleistungs-Vision-Language-Modell für medizinische Dokumente
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Quality and Processing Settings */}
                    <div className="bg-white border border-primary-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">⚙️ Verarbeitungseinstellungen</h4>

                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="font-medium text-primary-900">OpenCV verfügbar</h5>
                            <p className="text-sm text-primary-600">Erweiterte Bildanalyse für Qualitätsbewertung</p>
                          </div>
                          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
                            ocrSettings.opencv_enabled ? 'bg-success-100 text-success-800' : 'bg-warning-100 text-warning-800'
                          }`}>
                            {ocrSettings.opencv_enabled ? '✅ Verfügbar' : '⚠️ Nicht verfügbar'}
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-primary-700">
                            Qualitätsschwelle: {Math.round((ocrSettings.confidence_threshold || 0.7) * 100)}%
                          </label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            step="5"
                            value={Math.round((ocrSettings.confidence_threshold || 0.7) * 100)}
                            onChange={(e) => handleOCRSettingsUpdate('confidence_threshold', parseInt(e.target.value) / 100)}
                            disabled={ocrSaving}
                            className="w-full h-2 bg-primary-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
                          />
                          <div className="flex justify-between text-xs text-primary-500">
                            <span>Niedrig</span>
                            <span>Hoch</span>
                          </div>
                          <p className="text-xs text-primary-500">
                            Ab diesem Wert wird lokale OCR durch Vision-KI ersetzt
                          </p>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="font-medium text-primary-900">Multi-File-Verarbeitung</h5>
                            <p className="text-sm text-primary-600">Mehrere Dateien zu einem Dokument zusammenführen (max: {ocrSettings.multi_file_max_count})</p>
                          </div>
                          <button
                            onClick={() => handleOCRSettingsUpdate('multi_file_enabled', !ocrSettings.multi_file_enabled)}
                            disabled={ocrSaving}
                            className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                              ocrSettings.multi_file_enabled ? 'bg-brand-600' : 'bg-primary-300'
                            } ${ocrSaving ? 'opacity-50' : ''}`}
                          >
                            <span
                              className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                                ocrSettings.multi_file_enabled ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="font-medium text-primary-900">Datei-Sequenzerkennung</h5>
                            <p className="text-sm text-primary-600">Intelligente Erkennung der Reihenfolge bei Multi-File-Verarbeitung</p>
                          </div>
                          <button
                            onClick={() => handleOCRSettingsUpdate('file_sequence_detection', !ocrSettings.file_sequence_detection)}
                            disabled={ocrSaving}
                            className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                              ocrSettings.file_sequence_detection ? 'bg-brand-600' : 'bg-primary-300'
                            } ${ocrSaving ? 'opacity-50' : ''}`}
                          >
                            <span
                              className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                                ocrSettings.file_sequence_detection ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-primary-700 mb-2">
                            Text-Zusammenführungsstrategie
                          </label>
                          <select
                            value={ocrSettings.medical_text_merging}
                            onChange={(e) => handleOCRSettingsUpdate('medical_text_merging', e.target.value)}
                            disabled={ocrSaving}
                            className="w-full px-3 py-2 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none disabled:opacity-50"
                          >
                            <option value="simple">📝 Einfach - Direktes Anhängen</option>
                            <option value="smart">🤖 Intelligent - Strukturerkennung</option>
                            <option value="medical_aware">🏥 Medizinisch - Spezialisierte Zusammenführung</option>
                          </select>
                          <p className="text-xs text-primary-500 mt-1">
                            Bestimmt, wie Texte aus mehreren Dateien zusammengeführt werden
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Pipeline Integration */}
                    <div className="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-green-900 mb-4">🔗 Pipeline-Integration</h4>
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-success-600" />
                          <span className="text-green-700">TEXT_EXTRACTION Schritt ist in der Pipeline aktiviert</span>
                        </div>
                        <div className="flex items-center space-x-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-success-600" />
                          <span className="text-green-700">OCR-Nachbearbeitung über universelle Prompts konfiguriert</span>
                        </div>
                        <div className="flex items-center space-x-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-success-600" />
                          <span className="text-green-700">Multi-File-Support für zusammenhängende Dokumente</span>
                        </div>
                      </div>
                      <div className="mt-4 p-3 bg-green-100 rounded-lg">
                        <p className="text-sm text-green-800">
                          <strong>Hinweis:</strong> OCR-Einstellungen werden automatisch mit der bestehenden Pipeline synchronisiert.
                          Änderungen wirken sich sofort auf neue Dokumentverarbeitungen aus.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : null
              ) : activeTab === 'optimization' ? (
                settingsLoading ? (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
                    <p className="text-primary-600">Einstellungen werden geladen...</p>
                  </div>
                ) : settingsError ? (
                  <div className="text-center py-12">
                    <AlertCircle className="w-16 h-16 text-error-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-error-700 mb-2">Fehler beim Laden</h3>
                    <p className="text-error-600 mb-4">{settingsError}</p>
                    <button
                      onClick={loadPipelineSettings}
                      className="btn-primary"
                    >
                      Erneut versuchen
                    </button>
                  </div>
                ) : pipelineSettings ? (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-xl font-bold text-primary-900">Pipeline-Optimierung</h3>
                        <p className="text-sm text-primary-600">
                          Konfigurieren Sie die Performance-Optimierungen des Verarbeitungssystems
                        </p>
                      </div>
                      <button
                        onClick={handleClearCache}
                        className="btn-secondary"
                      >
                        🗑️ Cache Leeren
                      </button>
                    </div>

                    {/* Core Pipeline Settings */}
                    <div className="bg-white border border-primary-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">🚀 Kern-Optimierungen</h4>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h5 className="font-medium text-primary-900">Optimierte Pipeline verwenden</h5>
                            <p className="text-sm text-primary-600">Aktiviert Caching, parallele Verarbeitung und Performance-Verbesserungen</p>
                          </div>
                          <button
                            onClick={() => handleSettingsUpdate('use_optimized_pipeline', !pipelineSettings.use_optimized_pipeline)}
                            disabled={updatingSettings}
                            className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 ${
                              pipelineSettings.use_optimized_pipeline ? 'bg-brand-600' : 'bg-primary-300'
                            } ${updatingSettings ? 'opacity-50' : ''}`}
                          >
                            <span
                              className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                                pipelineSettings.use_optimized_pipeline ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                        </div>

                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-primary-700">
                            Cache Timeout (Sekunden): {pipelineSettings.pipeline_cache_timeout}
                          </label>
                          <input
                            type="range"
                            min="60"
                            max="3600"
                            step="60"
                            value={pipelineSettings.pipeline_cache_timeout}
                            onChange={(e) => handleSettingsUpdate('pipeline_cache_timeout', parseInt(e.target.value))}
                            className="w-full h-2 bg-primary-200 rounded-lg appearance-none cursor-pointer"
                          />
                          <div className="flex justify-between text-xs text-primary-500">
                            <span>1 Min</span>
                            <span>60 Min</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Individual Step Controls */}
                    <div className="bg-white border border-primary-200 rounded-xl p-6">
                      <div className="mb-6">
                        <h4 className="text-lg font-semibold text-primary-900 mb-4">⚙️ Pipeline-Schritte</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                            <p className="text-sm text-blue-800">
                              <strong>🌐 Universelle Schritte:</strong> Gelten für alle Dokumenttypen gleichzeitig
                            </p>
                          </div>
                          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                            <p className="text-sm text-green-800">
                              <strong>📄 Dokument-spezifische Schritte:</strong> Verwenden unterschiedliche Prompts je Dokumenttyp
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Universal Steps */}
                      <div className="mb-6">
                        <h5 className="text-md font-semibold text-blue-900 mb-3 flex items-center">
                          🌐 Universelle Schritte (0-4, 8-9)
                        </h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {[
                            { key: 'enable_text_extraction', name: '0. Text-Extraktion (Bedingt)', desc: '📄 Nur bei Bildern/PDFs - Springt über bei Text-Dateien', order: 0, conditional: true },
                            { key: 'enable_medical_validation', name: '1. Medizinische Validierung', desc: 'Prüft ob Text medizinischen Inhalt enthält', order: 1 },
                            { key: 'enable_classification', name: '2. Klassifizierung', desc: 'Erkennt Dokumenttyp (Arztbrief, Befund, etc.)', order: 2 },
                            { key: 'enable_preprocessing', name: '3. Vorverarbeitung', desc: 'Entfernt persönliche Daten (PII)', order: 3 },
                            { key: 'enable_language_translation', name: '7. Sprachübersetzung', desc: 'Übersetzt in Zielsprache', order: 7 },
                            { key: 'enable_final_check', name: '8. Finale Kontrolle', desc: 'Qualitätssicherung und Validierung', order: 8 }
                          ].map(({ key, name, desc, order, conditional }) => (
                            <div key={key} className={`flex items-center justify-between p-3 rounded-lg border ${
                              conditional ? 'bg-yellow-50 border-yellow-200' : 'bg-blue-50 border-blue-200'
                            }`}>
                              <div>
                                <div className="flex items-center space-x-2">
                                  <h6 className={`text-sm font-medium ${
                                    conditional ? 'text-yellow-900' : 'text-blue-900'
                                  }`}>{name}</h6>
                                  {conditional && (
                                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                      Auto
                                    </span>
                                  )}
                                </div>
                                <p className={`text-xs ${
                                  conditional ? 'text-yellow-600' : 'text-blue-600'
                                }`}>{desc}</p>
                              </div>
                              <button
                                onClick={() => handleSettingsUpdate(key as keyof PipelineSettings, !(pipelineSettings as any)[key])}
                                disabled={updatingSettings}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                                  (pipelineSettings as any)[key] ? 'bg-blue-600' : 'bg-blue-300'
                                } ${updatingSettings ? 'opacity-50' : ''}`}
                              >
                                <span
                                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                                    (pipelineSettings as any)[key] ? 'translate-x-5' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Document-Specific Steps */}
                      <div>
                        <h5 className="text-md font-semibold text-green-900 mb-3 flex items-center">
                          📄 Dokument-spezifische Schritte (4-6, 9)
                        </h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {[
                            { key: 'enable_translation', name: '4. Übersetzung', desc: 'Übersetzt in verständliche Sprache (je Dokumenttyp unterschiedlich)', order: 4 },
                            { key: 'enable_fact_check', name: '5. Faktenprüfung', desc: 'Prüft medizinische Korrektheit (je Dokumenttyp unterschiedlich)', order: 5 },
                            { key: 'enable_grammar_check', name: '6. Grammatikprüfung', desc: 'Korrigiert Grammatik und Rechtschreibung', order: 6 },
                            { key: 'enable_formatting', name: '9. Formatierung', desc: 'Strukturiert und formatiert den Text (je Dokumenttyp unterschiedlich)', order: 9 }
                          ].map(({ key, name, desc, order }) => (
                            <div key={key} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                              <div>
                                <h6 className="text-sm font-medium text-green-900">{name}</h6>
                                <p className="text-xs text-green-600">{desc}</p>
                              </div>
                              <button
                                onClick={() => handleSettingsUpdate(key as keyof PipelineSettings, !(pipelineSettings as any)[key])}
                                disabled={updatingSettings}
                                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 ${
                                  (pipelineSettings as any)[key] ? 'bg-green-600' : 'bg-green-300'
                                } ${updatingSettings ? 'opacity-50' : ''}`}
                              >
                                <span
                                  className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                                    (pipelineSettings as any)[key] ? 'translate-x-5' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Performance Stats */}
                    {pipelineStats && (
                      <div className="bg-gradient-to-br from-brand-50 to-accent-50 border border-brand-200 rounded-xl p-6">
                        <h4 className="text-lg font-semibold text-primary-900 mb-4">📊 Performance-Statistiken</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-3">
                            <div>
                              <span className="text-sm font-medium text-primary-700">Pipeline-Modus:</span>
                              <p className="text-lg font-bold text-brand-600 capitalize">{pipelineStats.pipeline_mode || 'Unbekannt'}</p>
                            </div>
                            <div>
                              <span className="text-sm font-medium text-primary-700">Cache Einträge:</span>
                              <p className="text-lg font-bold text-success-600">{pipelineStats.cache_statistics?.active_entries || 0} / {pipelineStats.cache_statistics?.total_entries || 0}</p>
                            </div>
                          </div>
                          <div className="space-y-3">
                            <div>
                              <span className="text-sm font-medium text-primary-700">Cache Timeout:</span>
                              <p className="text-lg font-bold text-primary-600">{pipelineStats.cache_statistics?.cache_timeout_seconds || 0}s</p>
                            </div>
                            <div>
                              <span className="text-sm font-medium text-primary-700">Abgelaufene Einträge:</span>
                              <p className="text-lg font-bold text-warning-600">{pipelineStats.cache_statistics?.expired_entries || 0}</p>
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 pt-4 border-t border-primary-200">
                          <h5 className="font-semibold text-primary-900 mb-2">Optimierungen aktiv:</h5>
                          <div className="grid grid-cols-1 gap-2">
                            {Object.entries(pipelineStats.performance_improvements).map(([key, description]) => (
                              <div key={key} className="flex items-center space-x-2 text-sm">
                                <CheckCircle className="w-4 h-4 text-success-600" />
                                <span className="text-primary-700">{description}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : null
              ) : activeTab === 'statistics' ? (
                pipelineStats && pipelineStats.cache_statistics ? (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-xl font-bold text-primary-900">📊 Pipeline-Statistiken</h3>
                      <p className="text-sm text-primary-600">
                        Detaillierte Analyse der Verarbeitungsstatistiken und Performance-Metriken
                      </p>
                    </div>

                    {/* Overview Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-xl p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-blue-700">Pipeline-Modus</p>
                            <p className="text-2xl font-bold text-blue-900 capitalize">{pipelineStats.pipeline_mode || 'Unbekannt'}</p>
                          </div>
                          <div className="w-12 h-12 bg-blue-200 rounded-lg flex items-center justify-center">
                            <span className="text-blue-600 text-xl">⚙️</span>
                          </div>
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-xl p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-green-700">Cache Einträge</p>
                            <p className="text-2xl font-bold text-green-900">{pipelineStats.cache_statistics?.active_entries || 0}</p>
                            <p className="text-xs text-green-600">von {pipelineStats.cache_statistics?.total_entries || 0} gesamt</p>
                          </div>
                          <div className="w-12 h-12 bg-green-200 rounded-lg flex items-center justify-center">
                            <span className="text-green-600 text-xl">💾</span>
                          </div>
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-xl p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-purple-700">Cache Timeout</p>
                            <p className="text-2xl font-bold text-purple-900">{pipelineStats.cache_statistics?.cache_timeout_seconds || 0}s</p>
                            <p className="text-xs text-purple-600">{pipelineStats.cache_statistics?.expired_entries || 0} abgelaufen</p>
                          </div>
                          <div className="w-12 h-12 bg-purple-200 rounded-lg flex items-center justify-center">
                            <span className="text-purple-600 text-xl">⏱️</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Cache Statistics Detail */}
                    <div className="bg-white border border-primary-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">💾 Cache-Statistiken</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between py-2 border-b border-primary-100">
                            <span className="text-sm font-medium text-primary-700">Gesamte Einträge:</span>
                            <span className="text-sm font-bold text-primary-900">{pipelineStats.cache_statistics?.total_entries || 0}</span>
                          </div>
                          <div className="flex items-center justify-between py-2 border-b border-primary-100">
                            <span className="text-sm font-medium text-primary-700">Aktive Einträge:</span>
                            <span className="text-sm font-bold text-success-600">{pipelineStats.cache_statistics?.active_entries || 0}</span>
                          </div>
                          <div className="flex items-center justify-between py-2 border-b border-primary-100">
                            <span className="text-sm font-medium text-primary-700">Abgelaufene Einträge:</span>
                            <span className="text-sm font-bold text-warning-600">{pipelineStats.cache_statistics?.expired_entries || 0}</span>
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between py-2 border-b border-primary-100">
                            <span className="text-sm font-medium text-primary-700">Timeout-Einstellung:</span>
                            <span className="text-sm font-bold text-primary-900">{pipelineStats.cache_statistics?.cache_timeout_seconds || 0} Sekunden</span>
                          </div>
                          <div className="flex items-center justify-between py-2 border-b border-primary-100">
                            <span className="text-sm font-medium text-primary-700">Cache-Effizienz:</span>
                            <span className="text-sm font-bold text-brand-600">
                              {(pipelineStats.cache_statistics?.total_entries || 0) > 0
                                ? Math.round(((pipelineStats.cache_statistics?.active_entries || 0) / (pipelineStats.cache_statistics?.total_entries || 1)) * 100)
                                : 0}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Performance Improvements */}
                    <div className="bg-white border border-primary-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">🚀 Performance-Verbesserungen</h4>
                      <div className="grid grid-cols-1 gap-3">
                        {pipelineStats.performance_improvements && Object.keys(pipelineStats.performance_improvements).length > 0 ? (
                          Object.entries(pipelineStats.performance_improvements).map(([key, description]) => (
                            <div key={key} className="flex items-start space-x-3 p-3 bg-gradient-to-r from-success-50 to-green-50 border border-success-200 rounded-lg">
                              <div className="w-6 h-6 bg-success-100 rounded-full flex items-center justify-center mt-0.5">
                                <CheckCircle className="w-4 h-4 text-success-600" />
                              </div>
                              <div>
                                <p className="text-sm font-medium text-success-900 capitalize">{key.replace(/_/g, ' ')}</p>
                                <p className="text-sm text-success-700">{description}</p>
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-center py-4">
                            <p className="text-sm text-primary-500">Keine Performance-Verbesserungen verfügbar</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="bg-gradient-to-r from-accent-50 to-brand-50 border border-accent-200 rounded-xl p-6">
                      <h4 className="text-lg font-semibold text-primary-900 mb-4">🛠️ Aktionen</h4>
                      <div className="flex items-center space-x-4">
                        <button
                          onClick={loadPipelineStats}
                          className="btn-primary"
                        >
                          🔄 Statistiken aktualisieren
                        </button>
                        <button
                          onClick={handleClearCache}
                          className="btn-secondary"
                        >
                          🗑️ Cache leeren
                        </button>
                      </div>
                    </div>
                  </div>
                ) : pipelineStats ? (
                  <div className="text-center py-12">
                    <AlertCircle className="w-16 h-16 text-warning-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-warning-700 mb-2">Unvollständige Daten</h3>
                    <p className="text-warning-600 mb-4">
                      Pipeline-Statistiken sind verfügbar, aber die Cache-Daten sind unvollständig.
                    </p>
                    <button
                      onClick={loadPipelineStats}
                      className="btn-primary"
                    >
                      🔄 Erneut laden
                    </button>
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
                    <p className="text-primary-600">Pipeline-Statistiken werden geladen...</p>
                  </div>
                )
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EnhancedSettingsModal;