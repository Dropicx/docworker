/**
 * Reusable Header component with app switcher dropdown.
 *
 * Allows navigation between HealthLingo (document translation)
 * and GuidelineChat (RAG chatbot).
 */

import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Stethoscope,
  BookOpen,
  ChevronDown,
  User,
  Settings,
  LogOut,
  Shield,
  AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { HealthCheck } from '../types/api';

interface AppDefinition {
  id: string;
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  subtitle: string;
}

const apps: AppDefinition[] = [
  {
    id: 'healthlingo',
    name: 'HealthLingo',
    path: '/',
    icon: Stethoscope,
    subtitle: 'Dokumente verstehen',
  },
  {
    id: 'chat',
    name: 'GuidelineChat',
    path: '/chat',
    icon: BookOpen,
    subtitle: 'Leitlinien-Assistent',
  },
];

interface HeaderProps {
  health?: HealthCheck | null;
  onLogoClick?: () => void;
  showHealthIndicator?: boolean;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  onLogoClick,
  showHealthIndicator = true,
  subtitle,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuth();

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [showHealthDetails, setShowHealthDetails] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const healthDropdownRef = useRef<HTMLDivElement>(null);

  // Determine current app from path
  const currentApp =
    apps.find(app => {
      if (app.path === '/') {
        return location.pathname === '/';
      }
      return location.pathname.startsWith(app.path);
    }) || apps[0];

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
      if (
        healthDropdownRef.current &&
        !healthDropdownRef.current.contains(event.target as Node)
      ) {
        setShowHealthDetails(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleSettingsClick = () => {
    navigate('/settings');
  };

  const handleAppSwitch = (app: AppDefinition) => {
    setDropdownOpen(false);
    navigate(app.path);
  };

  const handleLogoClick = () => {
    if (onLogoClick) {
      onLogoClick();
    } else {
      navigate(currentApp.path);
    }
  };

  const getServiceStatus = (status: string) => {
    if (status === 'healthy' || status === 'configured') return 'ok';
    if (status === 'not_configured') return 'warning';
    if (status.startsWith('error')) return 'error';
    if (status.includes('active')) return 'ok';
    return 'unknown';
  };

  const getServiceIcon = (status: string) => {
    const s = getServiceStatus(status);
    if (s === 'ok') return '\u2713';
    if (s === 'warning') return '\u25CB';
    if (s === 'error') return '\u2717';
    return '?';
  };

  const getServiceColor = (status: string) => {
    const s = getServiceStatus(status);
    if (s === 'ok') return 'text-success-600';
    if (s === 'warning') return 'text-warning-600';
    if (s === 'error') return 'text-error-600';
    return 'text-neutral-500';
  };

  const formatServiceName = (name: string) => {
    const names: Record<string, string> = {
      mistral_ocr: 'Mistral OCR',
      ovh_api: 'OVH API',
      worker: 'Worker',
      redis: 'Redis',
      filesystem: 'Dateisystem',
      image_processing: 'Bildverarbeitung',
      pdf_processing: 'PDF-Verarbeitung',
    };
    return names[name] || name;
  };

  const renderHealthIndicator = () => {
    if (!health || !showHealthIndicator) return null;

    const isHealthy = health.status === 'healthy';
    const hasWarnings = health.status === 'degraded';
    const isAdmin = isAuthenticated && user?.role === 'admin';

    // Simple badge for non-admin users
    if (!isAdmin) {
      return (
        <div
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium ${
            isHealthy
              ? 'bg-success-50 text-success-700 ring-1 ring-success-200'
              : hasWarnings
                ? 'bg-warning-50 text-warning-700 ring-1 ring-warning-200'
                : 'bg-error-50 text-error-700 ring-1 ring-error-200'
          }`}
        >
          {isHealthy ? (
            <Shield className="w-3 h-3" />
          ) : (
            <AlertTriangle className="w-3 h-3" />
          )}
          <span>
            {isHealthy ? 'System bereit' : hasWarnings ? 'Eingeschrankt' : 'Systemfehler'}
          </span>
        </div>
      );
    }

    // Full dropdown for admin users
    const keyServices = ['mistral_ocr', 'ovh_api', 'worker'];
    const displayServices = keyServices.filter(s => health.services[s]);

    return (
      <div className="relative" ref={healthDropdownRef}>
        <button
          onClick={() => setShowHealthDetails(!showHealthDetails)}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-all hover:shadow-md ${
            isHealthy
              ? 'bg-success-50 text-success-700 ring-1 ring-success-200 hover:bg-success-100'
              : hasWarnings
                ? 'bg-warning-50 text-warning-700 ring-1 ring-warning-200 hover:bg-warning-100'
                : 'bg-error-50 text-error-700 ring-1 ring-error-200 hover:bg-error-100'
          }`}
        >
          {isHealthy ? (
            <Shield className="w-3 h-3" />
          ) : (
            <AlertTriangle className="w-3 h-3" />
          )}
          <span>
            {isHealthy ? 'System bereit' : hasWarnings ? 'Eingeschrankt' : 'Systemfehler'}
          </span>
          <ChevronDown
            className={`w-3 h-3 transition-transform ${showHealthDetails ? 'rotate-180' : ''}`}
          />
        </button>

        {showHealthDetails && (
          <div className="absolute right-0 top-full mt-2 w-64 bg-white rounded-xl shadow-xl border border-neutral-200 overflow-hidden z-50 animate-fade-in">
            <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200">
              <h4 className="text-sm font-semibold text-neutral-800">System-Status</h4>
              <p className="text-xs text-neutral-500">OCR & AI Services</p>
            </div>
            <div className="p-2">
              {displayServices.map(serviceName => {
                const status = health.services[serviceName];
                return (
                  <div
                    key={serviceName}
                    className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-neutral-50"
                  >
                    <span className="text-sm text-neutral-700">
                      {formatServiceName(serviceName)}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span className={`text-sm font-medium ${getServiceColor(status)}`}>
                        {getServiceIcon(status)}
                      </span>
                      <span className="text-xs text-neutral-500">
                        {status === 'healthy' || status === 'configured'
                          ? 'OK'
                          : status === 'not_configured'
                            ? 'Nicht konfiguriert'
                            : status.startsWith('error')
                              ? 'Fehler'
                              : status.includes('active')
                                ? status.match(/\d+/)?.[0] + ' aktiv'
                                : status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="px-4 py-2 bg-neutral-50 border-t border-neutral-200">
              <p className="text-xs text-neutral-500 text-center">
                Klicken Sie auserhalb, um zu schliesen
              </p>
            </div>
          </div>
        )}
      </div>
    );
  };

  const CurrentIcon = currentApp.icon;

  return (
    <header className="sticky top-0 z-50 header-blur">
      <div className="max-w-5xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Logo with App Switcher */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center space-x-2 sm:space-x-3 hover:opacity-80 transition-opacity group"
            >
              <div className="hero-gradient p-2 sm:p-3 rounded-xl sm:rounded-2xl shadow-soft">
                <CurrentIcon className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
              </div>
              <div className="text-left">
                <div className="flex items-center space-x-1">
                  <h1 className="text-lg sm:text-2xl font-bold text-primary-900 tracking-tight">
                    {currentApp.name}
                  </h1>
                  <ChevronDown
                    className={`w-4 h-4 text-primary-500 transition-transform ${
                      dropdownOpen ? 'rotate-180' : ''
                    }`}
                  />
                </div>
                <p className="text-xs sm:text-sm text-primary-600 font-medium">
                  {subtitle || currentApp.subtitle}
                </p>
              </div>
            </button>

            {/* App Switcher Dropdown */}
            {dropdownOpen && (
              <div className="absolute left-0 top-full mt-2 w-64 bg-white rounded-xl shadow-xl border border-neutral-200 overflow-hidden z-50 animate-fade-in">
                <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-200">
                  <h4 className="text-sm font-semibold text-neutral-800">Anwendungen</h4>
                </div>
                <div className="p-2">
                  {apps.map(app => {
                    const Icon = app.icon;
                    const isActive = app.id === currentApp.id;
                    return (
                      <button
                        key={app.id}
                        onClick={() => handleAppSwitch(app)}
                        className={`w-full flex items-center space-x-3 px-3 py-3 rounded-lg transition-colors ${
                          isActive
                            ? 'bg-brand-50 text-brand-700 ring-1 ring-brand-200'
                            : 'text-neutral-700 hover:bg-neutral-50'
                        }`}
                      >
                        <div
                          className={`p-2 rounded-lg ${
                            isActive ? 'bg-brand-100' : 'bg-neutral-100'
                          }`}
                        >
                          <Icon className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-medium">{app.name}</div>
                          <div className="text-xs text-neutral-500">{app.subtitle}</div>
                        </div>
                        {isActive && (
                          <div className="ml-auto">
                            <div className="w-2 h-2 bg-brand-500 rounded-full" />
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Right side: Health indicator & User menu */}
          <div className="flex items-center space-x-4">
            {renderHealthIndicator()}

            {/* User Menu */}
            {isAuthenticated && (
              <div className="flex items-center space-x-2">
                <div className="flex items-center space-x-2 px-3 py-1.5 bg-brand-50 rounded-lg">
                  <User className="w-4 h-4 text-brand-600" />
                  <span className="text-sm font-medium text-brand-700 hidden sm:inline">
                    {user?.full_name || user?.email}
                  </span>
                  <span className="text-xs text-brand-600 bg-brand-100 px-2 py-0.5 rounded-full">
                    {user?.role === 'admin' ? 'Admin' : 'User'}
                  </span>
                </div>
                <button
                  onClick={handleSettingsClick}
                  className="p-2 text-primary-600 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-all duration-200 group"
                  title="Einstellungen"
                >
                  <Settings className="w-5 h-5 group-hover:scale-110 transition-transform" />
                </button>
                <button
                  onClick={handleLogout}
                  className="p-2 text-primary-600 hover:text-error-600 hover:bg-error-50 rounded-lg transition-all duration-200 group"
                  title="Abmelden"
                >
                  <LogOut className="w-5 h-5 group-hover:scale-110 transition-transform" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
