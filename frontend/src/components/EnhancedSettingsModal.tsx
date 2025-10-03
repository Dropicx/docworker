import React, { useState, useEffect } from 'react';
import { X, Settings, AlertCircle, FileText, Workflow } from 'lucide-react';
import settingsService from '../services/settings';
import PipelineBuilder from './settings/PipelineBuilder';
import DocumentClassManager from './settings/DocumentClassManager';
import { pipelineApi } from '../services/pipelineApi';

interface EnhancedSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const EnhancedSettingsModal: React.FC<EnhancedSettingsModalProps> = ({ isOpen, onClose }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [authError, setAuthError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'pipeline' | 'classes'>('pipeline');

  // Check authentication on mount only if we have a token
  useEffect(() => {
    if (isOpen && settingsService.isAuthenticated()) {
      checkAuth();
    }
  }, [isOpen]);

  const checkAuth = async () => {
    try {
      const authenticated = await settingsService.checkAuth();
      setIsAuthenticated(authenticated);

      if (authenticated) {
        setAuthError('');
        // Sync token with pipeline API
        pipelineApi.updateToken(localStorage.getItem('settings_auth_token'));
      }
    } catch (error: any) {
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
        // Sync token with pipeline API
        pipelineApi.updateToken(response.session_token || null);
      } else {
        setAuthError(response.message || 'Authentifizierung fehlgeschlagen');
      }
    } catch (error: any) {
      setAuthError(error.message || 'Authentifizierung fehlgeschlagen');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    settingsService.clearToken();
    setIsAuthenticated(false);
    setAccessCode('');
    setAuthError('');
    pipelineApi.updateToken(null);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-7xl max-h-[90vh] bg-white rounded-2xl shadow-2xl border border-primary-200 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-primary-200 bg-gradient-to-r from-brand-50 to-accent-50">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-primary-900">Pipeline-Konfiguration</h2>
              <p className="text-sm text-primary-600">
                Konfigurieren Sie OCR-Engine und dynamische Pipeline-Schritte
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-primary-100 rounded-lg transition-colors"
          >
            <X className="w-6 h-6 text-primary-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {!isAuthenticated ? (
            /* Authentication Form */
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="w-full max-w-md space-y-6">
                <div className="text-center space-y-2">
                  <div className="w-16 h-16 bg-brand-100 rounded-full flex items-center justify-center mx-auto">
                    <Settings className="w-8 h-8 text-brand-600" />
                  </div>
                  <h3 className="text-xl font-bold text-primary-900">Authentifizierung erforderlich</h3>
                  <p className="text-sm text-primary-600">
                    Bitte geben Sie den Zugangscode ein, um auf die Pipeline-Einstellungen zuzugreifen
                  </p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label htmlFor="accessCode" className="block text-sm font-medium text-primary-700 mb-2">
                      Zugangscode
                    </label>
                    <input
                      id="accessCode"
                      type="password"
                      value={accessCode}
                      onChange={(e) => setAccessCode(e.target.value)}
                      className="w-full px-4 py-3 border border-primary-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                      placeholder="Geben Sie den Zugangscode ein"
                      required
                      disabled={isLoading}
                    />
                  </div>

                  {authError && (
                    <div className="flex items-center space-x-2 p-3 bg-error-50 border border-error-200 rounded-lg text-error-700">
                      <AlertCircle className="w-5 h-5" />
                      <span className="text-sm">{authError}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full btn-primary flex items-center justify-center space-x-2"
                  >
                    <Settings className="w-5 h-5" />
                    <span>{isLoading ? 'Authentifizierung...' : 'Anmelden'}</span>
                  </button>
                </form>

                <p className="text-xs text-center text-primary-500">
                  Der Zugangscode wird sicher in Ihrer Sitzung gespeichert
                </p>
              </div>
            </div>
          ) : (
            /* Pipeline Settings Content */
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Tabs */}
              <div className="border-b border-primary-200 bg-white px-8 pt-4">
                <div className="flex items-center justify-between">
                  <div className="flex space-x-1">
                    <button
                      onClick={() => setActiveTab('pipeline')}
                      className={`flex items-center space-x-2 px-6 py-3 rounded-t-lg font-medium transition-all ${
                        activeTab === 'pipeline'
                          ? 'bg-gradient-to-r from-brand-600 to-brand-700 text-white shadow-md'
                          : 'text-primary-600 hover:bg-primary-50'
                      }`}
                    >
                      <Workflow className="w-4 h-4" />
                      <span>Pipeline-Konfiguration</span>
                    </button>
                    <button
                      onClick={() => setActiveTab('classes')}
                      className={`flex items-center space-x-2 px-6 py-3 rounded-t-lg font-medium transition-all ${
                        activeTab === 'classes'
                          ? 'bg-gradient-to-r from-brand-600 to-brand-700 text-white shadow-md'
                          : 'text-primary-600 hover:bg-primary-50'
                      }`}
                    >
                      <FileText className="w-4 h-4" />
                      <span>Dokumentenklassen</span>
                    </button>
                  </div>

                  {/* Logout Button */}
                  <button
                    onClick={handleLogout}
                    className="px-4 py-2 text-sm text-primary-700 hover:bg-primary-100 rounded-lg transition-colors"
                  >
                    Abmelden
                  </button>
                </div>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
                <div className="max-w-6xl mx-auto">
                  {activeTab === 'pipeline' && <PipelineBuilder />}
                  {activeTab === 'classes' && <DocumentClassManager />}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnhancedSettingsModal;
