import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authApiService } from '../services/authApi';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'user' | 'admin';
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user && !!tokens;

  // Define logout and refreshToken with useCallback before they're used in useEffect
  const logout = useCallback(async (): Promise<void> => {
    try {
      if (tokens?.refresh_token) {
        await authApiService.logout(tokens.refresh_token);
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local logout even if API call fails
    } finally {
      // Clear local state and storage
      setUser(null);
      setTokens(null);
      localStorage.removeItem('auth_tokens');
      localStorage.removeItem('auth_user');
    }
  }, [tokens]);

  const refreshToken = useCallback(async (): Promise<void> => {
    if (!tokens?.refresh_token) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await authApiService.refreshToken(tokens.refresh_token);

      const newTokens = {
        ...tokens,
        access_token: response.access_token,
        refresh_token: response.refresh_token,
      };

      setTokens(newTokens);
      localStorage.setItem('auth_tokens', JSON.stringify(newTokens));
    } catch (error) {
      console.error('Token refresh failed:', error);
      // If refresh fails, logout user
      await logout();
      throw error;
    }
  }, [tokens, logout]);

  // Load stored tokens and user data on mount
  useEffect(() => {
    const loadStoredAuth = async () => {
      try {
        const storedTokens = localStorage.getItem('auth_tokens');
        const storedUser = localStorage.getItem('auth_user');

        // Check for valid JSON strings (not null, not "undefined", not empty)
        if (
          storedTokens &&
          storedUser &&
          storedTokens !== 'undefined' &&
          storedUser !== 'undefined' &&
          storedTokens !== 'null' &&
          storedUser !== 'null'
        ) {
          const parsedTokens = JSON.parse(storedTokens);
          const parsedUser = JSON.parse(storedUser);

          // Validate that parsed data is actually objects
          if (
            parsedTokens &&
            typeof parsedTokens === 'object' &&
            parsedUser &&
            typeof parsedUser === 'object' &&
            parsedTokens.access_token
          ) {
            // Verify tokens are still valid by getting current user
            try {
              const currentUser = await authApiService.getCurrentUser(
                parsedTokens.access_token
              );
              setTokens(parsedTokens);
              setUser(currentUser);
            } catch (error) {
              // Tokens are invalid, clear storage
              console.warn('Stored tokens invalid, clearing:', error);
              localStorage.removeItem('auth_tokens');
              localStorage.removeItem('auth_user');
            }
          } else {
            // Invalid data structure, clear storage
            console.warn('Invalid auth data structure, clearing');
            localStorage.removeItem('auth_tokens');
            localStorage.removeItem('auth_user');
          }
        } else if (storedTokens || storedUser) {
          // Partial or corrupted data, clear everything
          console.warn('Partial or corrupted auth data, clearing');
          localStorage.removeItem('auth_tokens');
          localStorage.removeItem('auth_user');
        }
      } catch (error) {
        console.error('Error loading stored auth:', error);
        // Clear corrupted data
        localStorage.removeItem('auth_tokens');
        localStorage.removeItem('auth_user');
      } finally {
        setIsLoading(false);
      }
    };

    loadStoredAuth();
  }, []);

  // Auto-refresh token before expiration
  useEffect(() => {
    if (!tokens) return;

    const refreshInterval = setInterval(async () => {
      try {
        await refreshToken();
      } catch (error) {
        console.error('Auto-refresh failed:', error);
        // If refresh fails, logout user
        await logout();
      }
    }, 14 * 60 * 1000); // Refresh every 14 minutes (tokens expire in 15)

    return () => clearInterval(refreshInterval);
  }, [tokens, refreshToken, logout]);

  // Listen for logout events from API interceptor
  useEffect(() => {
    const handleLogout = () => {
      setUser(null);
      setTokens(null);
      localStorage.removeItem('auth_tokens');
      localStorage.removeItem('auth_user');
    };

    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    try {
      setIsLoading(true);
      const response = await authApiService.login(email, password);
      
      setTokens(response.tokens);
      setUser(response.user);
      
      // Store in localStorage
      localStorage.setItem('auth_tokens', JSON.stringify(response.tokens));
      localStorage.setItem('auth_user', JSON.stringify(response.user));
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateUser = (updatedUser: User): void => {
    setUser(updatedUser);
    localStorage.setItem('auth_user', JSON.stringify(updatedUser));
  };

  const value: AuthContextType = {
    user,
    tokens,
    isLoading,
    isAuthenticated,
    login,
    logout,
    refreshToken,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
