import React, { useState, useEffect } from 'react';
import { X, Settings, Save, RotateCcw, TestTube, Download, Upload, Eye, EyeOff, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import settingsService from '../services/settings';
import { DocumentClass, DocumentPrompts, DocumentTypeInfo, PROMPT_STEPS } from '../types/settings';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
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

  // Check authentication on mount
  useEffect(() => {
    if (isOpen) {
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
    if (isAuthenticated && selectedDocumentType) {
      loadPrompts();
    }
  }, [selectedDocumentType, isAuthenticated]);

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
        [field]: value
      });
    }
  };

  const handleSavePrompts = async () => {
    if (!editedPrompts) return;
    
    setSaving(true);
    setSaveError('');
    setSaveSuccess(false);
    
    try {
      await settingsService.updatePrompts(selectedDocumentType, editedPrompts, 'admin');
      setPrompts(editedPrompts);
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
    
    setTestingPrompt(field);
    setTestLoading(true);
    setTestError('');
    setTestResult('');
    
    try {
      const response = await settingsService.testPrompt({
        prompt: editedPrompts[field],
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
          onClick={onClose}
        />
        
        {/* Modal */}
        <div className="relative w-full max-w-6xl bg-white rounded-2xl shadow-2xl border border-primary-200 max-h-[90vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-primary-200 bg-gradient-to-r from-brand-50 to-accent-50">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center">
                <Settings className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-primary-900">Prompt-Einstellungen</h2>
                <p className="text-sm text-primary-600">Verwalten Sie die KI-Prompts für verschiedene Dokumenttypen</p>
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
            {/* Left Sidebar - Document Types */}
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
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-primary-900">Dokumenttypen</h3>
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
                        className={`w-full text-left p-4 rounded-xl border transition-all ${
                          selectedDocumentType === type.id
                            ? 'border-brand-300 bg-brand-50 text-brand-900'
                            : 'border-primary-200 bg-white hover:border-primary-300 hover:bg-primary-50'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{type.icon}</span>
                          <div>
                            <div className="font-semibold text-sm">{type.name}</div>
                            <div className="text-xs text-primary-600 mt-1">{type.description}</div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right Content - Prompts Editor */}
            <div className="flex-1 p-6 overflow-y-auto">
              {!isAuthenticated ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <Settings className="w-16 h-16 text-primary-300 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-primary-700 mb-2">Anmeldung erforderlich</h3>
                    <p className="text-primary-500">Bitte melden Sie sich an, um die Prompt-Einstellungen zu verwalten.</p>
                  </div>
                </div>
              ) : promptsLoading ? (
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
                    {Object.entries(PROMPT_STEPS).map(([key, step]) => (
                      <div key={key} className="border border-primary-200 rounded-xl p-6 bg-white">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <h4 className="text-lg font-semibold text-primary-900">{step.name}</h4>
                            <p className="text-sm text-primary-600">{step.description}</p>
                          </div>
                          <button
                            onClick={() => handleTestPrompt(key as keyof DocumentPrompts)}
                            disabled={testLoading || !testSample.trim()}
                            className="btn-ghost disabled:opacity-50"
                          >
                            <TestTube className="w-4 h-4" />
                            Testen
                          </button>
                        </div>
                        
                        <textarea
                          value={editedPrompts[key as keyof DocumentPrompts] || ''}
                          onChange={(e) => handlePromptChange(key as keyof DocumentPrompts, e.target.value)}
                          className="w-full h-32 p-3 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none resize-none font-mono text-sm"
                          placeholder={step.placeholder}
                        />
                      </div>
                    ))}
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
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
