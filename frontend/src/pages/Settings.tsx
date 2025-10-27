import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Stethoscope,
  Settings as SettingsIcon,
  FileText,
  Workflow,
  Activity,
  ArrowLeft,
  User,
  LogOut,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import PipelineBuilder from '../components/settings/PipelineBuilder';
import DocumentClassManager from '../components/settings/DocumentClassManager';
import FlowerDashboard from '../components/settings/FlowerDashboard';
import Footer from '../components/Footer';
import { pipelineApi } from '../services/pipelineApi';

const Settings: React.FC = () => {
  const navigate = useNavigate();
  const { user, tokens, logout, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'pipeline' | 'classes' | 'monitoring'>('pipeline');
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

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const tabs = [
    { id: 'pipeline', label: 'Pipeline', icon: Workflow },
    { id: 'classes', label: 'Dokumentklassen', icon: FileText },
    { id: 'monitoring', label: 'Monitoring', icon: Activity },
  ] as const;

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 header-blur">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 sm:h-20">
            {/* Logo */}
            <button
              onClick={() => navigate('/')}
              className="flex items-center space-x-2 sm:space-x-3 hover:opacity-80 transition-opacity"
            >
              <div className="hero-gradient p-2 sm:p-3 rounded-xl sm:rounded-2xl shadow-soft">
                <Stethoscope className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
              </div>
              <div className="text-left">
                <h1 className="text-lg sm:text-2xl font-bold text-primary-900 tracking-tight">
                  HealthLingo
                </h1>
                <p className="text-xs sm:text-sm text-primary-600 font-medium">Einstellungen</p>
              </div>
            </button>

            {/* User Menu */}
            <div className="flex items-center space-x-2 sm:space-x-4">
              {user && (
                <div className="flex items-center space-x-2 px-3 py-1.5 bg-brand-50 rounded-lg">
                  <User className="w-4 h-4 text-brand-600" />
                  <span className="text-sm font-medium text-brand-700 hidden sm:inline">
                    {user.full_name || user.email}
                  </span>
                  <span className="text-xs text-brand-600 bg-brand-100 px-2 py-0.5 rounded-full">
                    {user.role === 'admin' ? 'Admin' : 'User'}
                  </span>
                </div>
              )}
              <button
                onClick={handleLogout}
                className="p-2 text-primary-600 hover:text-error-600 hover:bg-error-50 rounded-lg transition-all duration-200 group"
                title="Abmelden"
              >
                <LogOut className="w-5 h-5 group-hover:scale-110 transition-transform" />
              </button>
            </div>
          </div>
        </div>
      </header>

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
                    {activeTab === 'monitoring' && <FlowerDashboard />}
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
