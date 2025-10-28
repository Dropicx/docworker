/**
 * AuthContext Tests
 *
 * Comprehensive test suite for authentication context covering:
 * - Provider initialization and localStorage restoration
 * - Login with storage persistence
 * - Logout with API cleanup
 * - Token refresh (manual and auto-refresh)
 * - User updates
 * - useAuth hook validation
 * - Event listeners and data validation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { AuthProvider, useAuth } from './AuthContext';
import { authApiService } from '../services/authApi';
import { createMockUser, createMockAuthTokens } from '../test/helpers/testData';

// Mock authApiService
vi.mock('../services/authApi', () => ({
  authApiService: {
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}));

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Don't use fake timers by default - AuthContext has async operations
  });

  afterEach(() => {
    vi.clearAllTimers();
    localStorage.clear();
  });

  // Helper to render hook with AuthProvider
  const renderAuthHook = () => {
    return renderHook(() => useAuth(), {
      wrapper: ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>,
    });
  };

  // ==================== Hook Validation Tests ====================

  describe('useAuth Hook', () => {
    it('should throw error when used outside AuthProvider', () => {
      // Suppress console error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useAuth());
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleSpy.mockRestore();
    });

    it('should return auth context when used inside AuthProvider', () => {
      const { result } = renderAuthHook();

      expect(result.current).toHaveProperty('user');
      expect(result.current).toHaveProperty('tokens');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('isAuthenticated');
      expect(result.current).toHaveProperty('login');
      expect(result.current).toHaveProperty('logout');
      expect(result.current).toHaveProperty('refreshToken');
      expect(result.current).toHaveProperty('updateUser');
    });
  });

  // ==================== Initialization Tests ====================

  describe('Provider Initialization', () => {
    it('should initialize with no user and no tokens', async () => {
      const { result } = renderAuthHook();

      // Wait for initial load to complete
      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      expect(result.current.user).toBeNull();
      expect(result.current.tokens).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });

    it('should restore valid auth from localStorage', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      localStorage.setItem('auth_tokens', JSON.stringify(mockTokens));
      localStorage.setItem('auth_user', JSON.stringify(mockUser));

      vi.mocked(authApiService.getCurrentUser).mockResolvedValue(mockUser);

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.tokens).toEqual(mockTokens);
      expect(result.current.isAuthenticated).toBe(true);
      expect(authApiService.getCurrentUser).toHaveBeenCalledWith(mockTokens.access_token);
    });

    it('should clear invalid tokens from localStorage', async () => {
      const mockTokens = createMockAuthTokens();
      const mockUser = createMockUser();

      localStorage.setItem('auth_tokens', JSON.stringify(mockTokens));
      localStorage.setItem('auth_user', JSON.stringify(mockUser));

      vi.mocked(authApiService.getCurrentUser).mockRejectedValue(new Error('Invalid token'));

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      expect(result.current.user).toBeNull();
      expect(result.current.tokens).toBeNull();
      expect(localStorage.getItem('auth_tokens')).toBeNull();
      expect(localStorage.getItem('auth_user')).toBeNull();
    });

    it('should clear corrupted localStorage data', async () => {
      localStorage.setItem('auth_tokens', 'invalid-json');
      localStorage.setItem('auth_user', 'invalid-json');

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      expect(result.current.user).toBeNull();
      expect(result.current.tokens).toBeNull();
      expect(localStorage.getItem('auth_tokens')).toBeNull();
      expect(localStorage.getItem('auth_user')).toBeNull();
    });
  });

  // ==================== Login Tests ====================

  describe('Login', () => {
    it('should login successfully and store auth data', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });

      const { result } = renderAuthHook();

      // Wait for initial loading to complete
      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      expect(result.current.user).toEqual(mockUser);
      expect(result.current.tokens).toEqual(mockTokens);
      expect(result.current.isAuthenticated).toBe(true);
      expect(localStorage.getItem('auth_tokens')).toEqual(JSON.stringify(mockTokens));
      expect(localStorage.getItem('auth_user')).toEqual(JSON.stringify(mockUser));
    });

    it('should handle login failure', async () => {
      vi.mocked(authApiService.login).mockRejectedValue(new Error('Invalid credentials'));

      const { result } = renderAuthHook();

      // Wait for initial loading to complete
      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      await expect(async () => {
        await act(async () => {
          await result.current.login('test@example.com', 'wrong-password');
        });
      }).rejects.toThrow('Invalid credentials');

      expect(result.current.user).toBeNull();
      expect(result.current.tokens).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
    });
  });

  // ==================== Logout Tests ====================

  describe('Logout', () => {
    it('should logout successfully and clear all data', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });
      vi.mocked(authApiService.logout).mockResolvedValue({ message: 'Logged out' });

      const { result } = renderAuthHook();

      // Wait for initial loading
      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      // Login first
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Then logout
      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.tokens).toBeNull();
      expect(result.current.isAuthenticated).toBe(false);
      expect(localStorage.getItem('auth_tokens')).toBeNull();
      expect(localStorage.getItem('auth_user')).toBeNull();
      expect(authApiService.logout).toHaveBeenCalledWith(mockTokens.refresh_token);
    });

    it('should clear data even if API logout fails', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });
      vi.mocked(authApiService.logout).mockRejectedValue(new Error('API error'));

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      // Login
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      // Logout (should succeed locally even if API fails)
      await act(async () => {
        await result.current.logout();
      });

      expect(result.current.user).toBeNull();
      expect(result.current.tokens).toBeNull();
      expect(localStorage.getItem('auth_tokens')).toBeNull();
      expect(localStorage.getItem('auth_user')).toBeNull();
    });
  });

  // ==================== Token Refresh Tests ====================

  describe('Token Refresh', () => {
    it('should refresh token successfully', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();
      const newTokens = {
        ...mockTokens,
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      };

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });
      vi.mocked(authApiService.refreshToken).mockResolvedValue(newTokens);

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      // Login first
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      // Refresh token
      await act(async () => {
        await result.current.refreshToken();
      });

      expect(result.current.tokens).toEqual(newTokens);
      expect(JSON.parse(localStorage.getItem('auth_tokens')!)).toEqual(newTokens);
      expect(authApiService.refreshToken).toHaveBeenCalledWith(mockTokens.refresh_token);
    });

    it('should logout if token refresh fails', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });
      vi.mocked(authApiService.refreshToken).mockRejectedValue(new Error('Refresh failed'));
      vi.mocked(authApiService.logout).mockResolvedValue({ message: 'Logged out' });

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      // Login
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Try to refresh (should fail and trigger logout)
      let refreshError;
      try {
        await act(async () => {
          try {
            await result.current.refreshToken();
          } catch (err) {
            refreshError = err;
            // Wait a bit for the logout inside catch block to execute
            await new Promise(resolve => setTimeout(resolve, 100));
          }
        });
      } catch {
        // Ignore outer error
      }

      // Verify the refresh threw the expected error
      expect(refreshError).toEqual(new Error('Refresh failed'));

      // Wait for logout to complete (happens inside refreshToken catch block)
      await waitFor(
        () => {
          expect(result.current.user).toBeNull();
          expect(result.current.tokens).toBeNull();
        },
        { timeout: 3000 }
      );
    });

    it('should auto-refresh tokens every 14 minutes', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();
      const newTokens = {
        ...mockTokens,
        access_token: 'auto-refreshed-token',
      };

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });
      vi.mocked(authApiService.refreshToken).mockResolvedValue(newTokens);

      // Use fake timers from the start
      vi.useFakeTimers();

      const { result } = renderAuthHook();

      // Wait for initial load
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      // Login
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Fast-forward 14 minutes (auto-refresh interval)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(14 * 60 * 1000);
      });

      // Verify refresh was called
      expect(authApiService.refreshToken).toHaveBeenCalled();

      vi.useRealTimers();
    }, 10000); // Increase test timeout to 10s
  });

  // ==================== User Update Tests ====================

  describe('User Update', () => {
    it('should update user and localStorage', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      // Login
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      // Update user
      const updatedUser = { ...mockUser, full_name: 'Updated Name' };

      act(() => {
        result.current.updateUser(updatedUser);
      });

      expect(result.current.user).toEqual(updatedUser);
      expect(JSON.parse(localStorage.getItem('auth_user')!)).toEqual(updatedUser);
    }, 10000); // Increase test timeout to 10s
  });

  // ==================== Event Listener Tests ====================

  describe('Auth Event Listener', () => {
    it('should handle auth:logout event', async () => {
      const mockUser = createMockUser();
      const mockTokens = createMockAuthTokens();

      vi.mocked(authApiService.login).mockResolvedValue({
        user: mockUser,
        tokens: mockTokens,
      });

      const { result } = renderAuthHook();

      await waitFor(
        () => {
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 3000 }
      );

      // Login
      await act(async () => {
        await result.current.login('test@example.com', 'password');
      });

      expect(result.current.isAuthenticated).toBe(true);

      // Dispatch logout event
      await act(async () => {
        window.dispatchEvent(new Event('auth:logout'));
      });

      await waitFor(
        () => {
          expect(result.current.user).toBeNull();
          expect(result.current.tokens).toBeNull();
          expect(localStorage.getItem('auth_tokens')).toBeNull();
          expect(localStorage.getItem('auth_user')).toBeNull();
        },
        { timeout: 3000 }
      );
    }, 10000); // Increase test timeout to 10s
  });
});
