import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Settings as SettingsIcon,
  FileText,
  Workflow,
  Activity,
  ArrowLeft,
  Loader2,
  Users,
  DollarSign,
  MessageSquare,
  Brain,
} from 'lucide-react';
import Header from '../components/Header';
import { useAuth } from '../contexts/AuthContext';
import PipelineBuilder from '../components/settings/PipelineBuilder';
import DocumentClassManager from '../components/settings/DocumentClassManager';
import FlowerDashboard from '../components/settings/FlowerDashboard';
import UserManagement from '../components/settings/UserManagement';
import CostDashboard from '../components/settings/CostDashboard';
import FeedbackDashboard from '../components/settings/FeedbackDashboard';
import AIModelManager from '../components/settings/AIModelManager';
import Footer from '../components/Footer';
import { pipelineApi } from '../services/pipelineApi';

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { tokens, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<
    'pipeline' | 'classes' | 'costs' | 'feedback' | 'users' | 'monitoring' | 'models'
  >('pipeline');
  const [tokenReady, setTokenReady] = useState(false);

  // Sync token with pipeline API when authenticated
  useEffect(() => {
    if (tokens?.access_token) {
      pipelineApi.updateToken(tokens.access_token);
      setTokenReady(true);
    } else if (!isLoading) {
      // If not loading and no tokens, authentication failed
      console.warn('No tokens available after loading');
      setTokenReady(false);
    }
  }, [tokens, isLoading]);

  const tabs = [
    { id: 'pipeline', label: 'Pipeline', icon: Workflow },
    { id: 'classes', label: 'Dokumentklassen', icon: FileText },
    { id: 'costs', label: 'Kosten', icon: DollarSign },
    { id: 'feedback', label: 'Feedback', icon: MessageSquare },
    { id: 'users', label: 'Benutzer', icon: Users },
    { id: 'monitoring', label: 'Monitoring', icon: Activity },
    { id: 'models', label: 'AI Modelle', icon: Brain },
  ] as const;

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header subtitle="Einstellungen" />

      {/* Main Content */}
      <main className="flex-1 py-6 sm:py-8">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
          {/* Page Header */}
          <div className="mb-6">
            <button
              onClick={() => navigate('/')}
              className="inline-flex items-center space-x-2 text-primary-600 hover:text-brand-600 transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Zurück zur Hauptseite</span>
            </button>

            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl flex items-center justify-center">
                <SettingsIcon className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-2xl sm:text-3xl font-bold text-primary-900">
                  Pipeline-Konfiguration
                </h2>
                <p className="text-sm text-primary-600">
                  Konfigurieren Sie OCR-Engine und dynamische Pipeline-Schritte
                </p>
              </div>
            </div>
          </div>

          {/* Settings Content */}
          <div className="bg-white rounded-2xl shadow-xl border border-primary-200 overflow-hidden">
            <div className="flex flex-col md:flex-row min-h-[600px]">
              {/* Sidebar Navigation */}
              <div className="w-full md:w-64 bg-neutral-50 border-b md:border-b-0 md:border-r border-neutral-200 p-4">
                <nav className="space-y-2">
                  {tabs.map(tab => {
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

              {/* Main Content Area */}
              <div className="flex-1 overflow-y-auto p-6">
                {isLoading || !tokenReady ? (
                  <div className="flex items-center justify-center h-full min-h-[400px]">
                    <div className="flex flex-col items-center space-y-3">
                      <Loader2 className="w-8 h-8 animate-spin text-brand-600" />
                      <span className="text-sm text-neutral-600">Lade Einstellungen...</span>
                    </div>
                  </div>
                ) : (
                  <>
                    {activeTab === 'pipeline' && <PipelineBuilder />}
                    {activeTab === 'classes' && <DocumentClassManager />}
                    {activeTab === 'costs' && <CostDashboard />}
                    {activeTab === 'feedback' && <FeedbackDashboard />}
                    {activeTab === 'users' && <UserManagement />}
                    {activeTab === 'monitoring' && <FlowerDashboard />}
                    {activeTab === 'models' && <AIModelManager />}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Settings;
