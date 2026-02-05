import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Eye, EyeOff, AlertCircle, Loader2, Stethoscope } from 'lucide-react';
import Header from '../components/Header';

const Login: React.FC = () => {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, authLoading, navigate, location]);

  // Listen for logout events from API interceptor
  useEffect(() => {
    const handleLogout = () => {
      setError(t('login.sessionExpired'));
    };

    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, [t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      // Navigation will be handled by useEffect
    } catch (error) {
      setError(error instanceof Error ? error.message : t('login.failed'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToHome = () => {
    navigate('/');
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex items-center justify-center">
        <div className="flex items-center space-x-3">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
          <span className="text-lg text-neutral-700">{t('login.loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header showHealthIndicator={false} />

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {/* Login Card */}
          <div className="card-elevated">
            <div className="card-body">
              <div className="text-center mb-8">
                <div className="w-16 h-16 bg-gradient-to-br from-brand-500 to-brand-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Stethoscope className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-primary-900 mb-2">{t('login.title')}</h2>
                <p className="text-primary-600">
                  {t('login.description')}
                </p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="mb-6 p-4 bg-error-50 border border-error-200 rounded-lg flex items-start space-x-3">
                  <AlertCircle className="w-5 h-5 text-error-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-error-700">{error}</p>
                </div>
              )}

              {/* Login Form */}
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-neutral-700 mb-2"
                  >
                    {t('login.email')}
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-neutral-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none transition-colors"
                    placeholder={t('login.emailPlaceholder')}
                    disabled={isLoading}
                  />
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="block text-sm font-medium text-neutral-700 mb-2"
                  >
                    {t('login.password')}
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      required
                      className="w-full px-4 py-3 pr-12 border border-neutral-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none transition-colors"
                      placeholder={t('login.passwordPlaceholder')}
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition-colors"
                      disabled={isLoading}
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading || !email || !password}
                  className="w-full btn-primary flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>{t('login.submitting')}</span>
                    </>
                  ) : (
                    <span>{t('login.submit')}</span>
                  )}
                </button>
              </form>

              {/* Back to Home */}
              <div className="mt-6 text-center">
                <button
                  onClick={handleBackToHome}
                  className="text-sm text-neutral-600 hover:text-brand-600 transition-colors"
                  disabled={isLoading}
                >
                  {t('login.backToHome')}
                </button>
              </div>
            </div>
          </div>

          {/* Info Card */}
          <div className="mt-6 p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
            <div className="text-center">
              <h3 className="text-sm font-medium text-neutral-900 mb-1">{t('login.noAccess')}</h3>
              <p className="text-xs text-neutral-600">
                {t('login.contactAdmin')}
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Login;
