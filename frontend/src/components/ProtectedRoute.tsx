import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2, AlertCircle } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'user' | 'admin';
  fallback?: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole, fallback }) => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex items-center justify-center">
        <div className="flex items-center space-x-3">
          <Loader2 className="w-6 h-6 animate-spin text-brand-600" />
          <span className="text-lg text-neutral-700">Lade...</span>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated (unless fallback is provided)
  if (!isAuthenticated) {
    if (fallback) {
      return <>{fallback}</>;
    }
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role requirements
  if (requiredRole && user?.role !== requiredRole && user?.role !== 'admin') {
    // Admin can access everything, but regular users need specific role
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex items-center justify-center">
        <div className="max-w-md mx-auto px-4">
          <div className="card-elevated border-error-200/50 bg-gradient-to-br from-error-50/50 to-white">
            <div className="card-body text-center">
              <div className="w-16 h-16 bg-gradient-to-br from-error-500 to-error-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-error-900 mb-2">Zugriff verweigert</h2>
              <p className="text-error-700 mb-6">
                Sie haben nicht die erforderlichen Berechtigungen, um auf diese Seite zuzugreifen.
              </p>
              <div className="space-y-3">
                <div className="text-sm text-neutral-600">
                  <p>
                    <strong>Ihre Rolle:</strong>{' '}
                    {user?.role === 'user' ? 'Benutzer' : 'Administrator'}
                  </p>
                  <p>
                    <strong>Erforderlich:</strong>{' '}
                    {requiredRole === 'admin' ? 'Administrator' : 'Benutzer oder Administrator'}
                  </p>
                </div>
                <button onClick={() => window.history.back()} className="btn-primary">
                  Zurück
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;
