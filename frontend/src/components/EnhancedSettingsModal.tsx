import React, { useState, useEffect } from 'react';
import { X, Settings, AlertCircle, FileText, Workflow, Activity } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import ProtectedRoute from './ProtectedRoute';
import PipelineBuilder from './settings/PipelineBuilder';
import DocumentClassManager from './settings/DocumentClassManager';
import FlowerDashboard from './settings/FlowerDashboard';
import { pipelineApi } from '../services/pipelineApi';

interface EnhancedSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsContent: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'pipeline' | 'classes' | 'monitoring'>('pipeline');

  // Sync token with pipeline API when authenticated
  useEffect(() => {
    const storedTokens = localStorage.getItem('auth_tokens');
    if (storedTokens) {
      try {
        const tokens = JSON.parse(storedTokens);
        pipelineApi.updateToken(tokens.access_token);
      } catch (error) {
        console.error('Error parsing stored tokens:', error);
      }
    }
  }, []);

  const tabs = [
    { id: 'pipeline', label: 'Pipeline', icon: Workflow },
    { id: 'classes', label: 'Dokumentklassen', icon: FileText },
    { id: 'monitoring', label: 'Monitoring', icon: Activity },
  ] as const;

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
              {user && (
                <p className="text-xs text-brand-600 mt-1">
                  Angemeldet als: {user.full_name || user.email} ({user.role === 'admin' ? 'Administrator' : 'Benutzer'})
                </p>
              )}
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
          {/* Sidebar */}
          <div className="w-64 bg-neutral-50 border-r border-neutral-200 p-4">
            <nav className="space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-colors ${
                      activeTab === tab.id
                        ? 'bg-brand-100 text-brand-700 border border-brand-200'
                        : 'text-neutral-600 hover:bg-neutral-100'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === 'pipeline' && <PipelineBuilder />}
            {activeTab === 'classes' && <DocumentClassManager />}
            {activeTab === 'monitoring' && <FlowerDashboard />}
          </div>
        </div>
      </div>
    </div>
  );
};

const EnhancedSettingsModal: React.FC<EnhancedSettingsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <ProtectedRoute requiredRole="user" fallback={
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
        <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-primary-200">
          <div className="p-6 text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-error-500 to-error-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-error-900 mb-2">
              Anmeldung erforderlich
            </h2>
            <p className="text-error-700 mb-6">
              Sie müssen angemeldet sein, um auf die Einstellungen zuzugreifen.
            </p>
            <div className="space-y-3">
              <a
                href="/login"
                className="block w-full btn-primary text-center"
              >
                Anmelden
              </a>
              <button
                onClick={onClose}
                className="block w-full px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors"
              >
                Abbrechen
              </button>
            </div>
          </div>
        </div>
      </div>
    }>
      <SettingsContent onClose={onClose} />
    </ProtectedRoute>
  );
};

export default EnhancedSettingsModal;