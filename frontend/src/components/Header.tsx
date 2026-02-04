import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Stethoscope, User, Settings, LogOut, Shield, AlertTriangle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { HealthCheck } from '../types/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

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
  const { isAuthenticated, user, logout } = useAuth();

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

  const handleLogoClick = () => {
    if (onLogoClick) {
      onLogoClick();
    } else {
      navigate('/');
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
        <Badge
          variant="outline"
          className={
            isHealthy
              ? 'bg-success-50 text-success-700 border-success-200'
              : hasWarnings
                ? 'bg-warning-50 text-warning-700 border-warning-200'
                : 'bg-error-50 text-error-700 border-error-200'
          }
        >
          {isHealthy ? (
            <Shield className="w-3 h-3 mr-1" />
          ) : (
            <AlertTriangle className="w-3 h-3 mr-1" />
          )}
          {isHealthy ? 'System bereit' : hasWarnings ? 'Eingeschrankt' : 'Systemfehler'}
        </Badge>
      );
    }

    // Full dropdown for admin users
    const keyServices = ['mistral_ocr', 'ovh_api', 'worker'];
    const displayServices = keyServices.filter(s => health.services[s]);

    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-auto px-3 py-1.5 rounded-full">
            <Badge
              variant="outline"
              className={`cursor-pointer ${
                isHealthy
                  ? 'bg-success-50 text-success-700 border-success-200 hover:bg-success-100'
                  : hasWarnings
                    ? 'bg-warning-50 text-warning-700 border-warning-200 hover:bg-warning-100'
                    : 'bg-error-50 text-error-700 border-error-200 hover:bg-error-100'
              }`}
            >
              {isHealthy ? (
                <Shield className="w-3 h-3 mr-1" />
              ) : (
                <AlertTriangle className="w-3 h-3 mr-1" />
              )}
              {isHealthy ? 'System bereit' : hasWarnings ? 'Eingeschrankt' : 'Systemfehler'}
            </Badge>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel>
            <div>
              <p className="text-sm font-semibold">System-Status</p>
              <p className="text-xs text-neutral-500 font-normal">OCR & AI Services</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {displayServices.map(serviceName => {
            const serviceStatus = health.services[serviceName];
            return (
              <DropdownMenuItem
                key={serviceName}
                className="flex items-center justify-between cursor-default"
              >
                <span className="text-sm text-neutral-700">{formatServiceName(serviceName)}</span>
                <div className="flex items-center space-x-2">
                  <span className={`text-sm font-medium ${getServiceColor(serviceStatus)}`}>
                    {getServiceIcon(serviceStatus)}
                  </span>
                  <span className="text-xs text-neutral-500">
                    {serviceStatus === 'healthy' || serviceStatus === 'configured'
                      ? 'OK'
                      : serviceStatus === 'not_configured'
                        ? 'Nicht konfiguriert'
                        : serviceStatus.startsWith('error')
                          ? 'Fehler'
                          : serviceStatus.includes('active')
                            ? serviceStatus.match(/\d+/)?.[0] + ' aktiv'
                            : serviceStatus}
                  </span>
                </div>
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuContent>
      </DropdownMenu>
    );
  };

  return (
    <header className="sticky top-0 z-50 header-blur">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Logo */}
          <button
            onClick={handleLogoClick}
            className="flex items-center space-x-2 sm:space-x-3 hover:opacity-80 transition-opacity"
          >
            <div className="hero-gradient p-2 sm:p-3 rounded-xl sm:rounded-2xl shadow-soft">
              <Stethoscope className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
            </div>
            <div className="text-left">
              <h1 className="text-lg sm:text-2xl font-bold text-primary-900 tracking-tight">
                HealthLingo
              </h1>
              <p className="text-xs sm:text-sm text-primary-600 font-medium">
                {subtitle || 'Dokumente verstehen'}
              </p>
            </div>
          </button>

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
                  <Badge
                    variant="outline"
                    className="text-xs bg-brand-100 text-brand-600 border-brand-200"
                  >
                    {user?.role === 'admin' ? 'Admin' : 'User'}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleSettingsClick}
                  title="Einstellungen"
                  className="text-primary-600 hover:text-brand-600 hover:bg-brand-50"
                >
                  <Settings className="w-5 h-5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleLogout}
                  title="Abmelden"
                  className="text-primary-600 hover:text-error-600 hover:bg-error-50"
                >
                  <LogOut className="w-5 h-5" />
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
