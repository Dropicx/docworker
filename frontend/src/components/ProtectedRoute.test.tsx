/**
 * ProtectedRoute Component Tests
 *
 * Comprehensive test suite covering:
 * - Loading state display
 * - Authenticated access (renders children)
 * - Unauthenticated redirect to login
 * - Unauthenticated fallback rendering
 * - Role-based access control (user, admin)
 * - Access denied UI and messaging
 * - Fallback for insufficient permissions
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter, userEvent } from '../test/helpers/renderWithProviders';
import { createMockUser } from '../test/helpers/testData';
import ProtectedRoute from './ProtectedRoute';
import * as AuthContext from '../contexts/AuthContext';

// Mock the entire AuthContext module
vi.mock('../contexts/AuthContext', async () => {
  const actual = await vi.importActual('../contexts/AuthContext');
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

describe('ProtectedRoute Component', () => {
  const mockNavigate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useNavigate
    vi.mock('react-router-dom', async () => {
      const actual = await vi.importActual('react-router-dom');
      return {
        ...actual,
        useNavigate: () => mockNavigate,
      };
    });
  });

  // ==================== Loading State Tests ====================

  describe('Loading State', () => {
    it('should show loading spinner when isLoading is true', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: true,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Lade...')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('should show spinner icon in loading state', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: true,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      const { container } = renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      );

      // Check for spinner (lucide-react Loader2 has animate-spin class)
      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  // ==================== Authenticated Access Tests ====================

  describe('Authenticated Access', () => {
    it('should render children when user is authenticated', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    it('should render children when admin is authenticated', () => {
      const mockUser = createMockUser({ role: 'admin' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute>
          <div>Admin Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Admin Content')).toBeInTheDocument();
    });
  });

  // ==================== Unauthenticated Redirect Tests ====================

  describe('Unauthenticated Access', () => {
    it('should redirect to login when not authenticated', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>,
        { route: '/dashboard' }
      );

      // Navigate component will redirect, check that children are not rendered
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });

    it('should show fallback when not authenticated and fallback provided', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute fallback={<div>Please log in to continue</div>}>
          <div>Protected Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Please log in to continue')).toBeInTheDocument();
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  // ==================== Role-Based Access Tests ====================

  describe('Role-Based Access Control', () => {
    it('should allow user access when requiredRole is user', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="user">
          <div>User Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('User Content')).toBeInTheDocument();
    });

    it('should allow admin access to user-only routes', () => {
      const mockUser = createMockUser({ role: 'admin' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="user">
          <div>User Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('User Content')).toBeInTheDocument();
    });

    it('should allow admin access when requiredRole is admin', () => {
      const mockUser = createMockUser({ role: 'admin' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Admin Only Content')).toBeInTheDocument();
    });

    it('should deny user access to admin-only routes', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      expect(screen.queryByText('Admin Only Content')).not.toBeInTheDocument();
      expect(screen.getByText('Zugriff verweigert')).toBeInTheDocument();
    });
  });

  // ==================== Access Denied UI Tests ====================

  describe('Access Denied UI', () => {
    it('should show access denied message with correct role info', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Zugriff verweigert')).toBeInTheDocument();
      expect(
        screen.getByText('Sie haben nicht die erforderlichen Berechtigungen, um auf diese Seite zuzugreifen.')
      ).toBeInTheDocument();
      expect(screen.getByText(/Ihre Rolle:/)).toBeInTheDocument();
      expect(screen.getByText(/Benutzer/)).toBeInTheDocument();
      expect(screen.getByText(/Erforderlich:/)).toBeInTheDocument();
      expect(screen.getByText(/Administrator/)).toBeInTheDocument();
    });

    it('should show back button in access denied UI', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      const backButton = screen.getByText('Zurück');
      expect(backButton).toBeInTheDocument();
    });

    it('should call window.history.back when back button clicked', async () => {
      const user = userEvent.setup();
      const mockUser = createMockUser({ role: 'user' });
      const mockHistoryBack = vi.fn();
      window.history.back = mockHistoryBack;

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      const backButton = screen.getByText('Zurück');
      await user.click(backButton);

      expect(mockHistoryBack).toHaveBeenCalledTimes(1);
    });

    it('should show alert icon in access denied UI', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      const { container } = renderWithRouter(
        <ProtectedRoute requiredRole="admin">
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      // Check for lucide-react AlertCircle icon
      const alertIcon = container.querySelector('svg');
      expect(alertIcon).toBeInTheDocument();
    });
  });

  // ==================== Role-Based Fallback Tests ====================

  describe('Role-Based Fallback', () => {
    it('should show fallback when user lacks required role and fallback provided', () => {
      const mockUser = createMockUser({ role: 'user' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin" fallback={<div>Insufficient permissions</div>}>
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Insufficient permissions')).toBeInTheDocument();
      expect(screen.queryByText('Admin Only Content')).not.toBeInTheDocument();
      expect(screen.queryByText('Zugriff verweigert')).not.toBeInTheDocument();
    });

    it('should not show fallback when user has sufficient role', () => {
      const mockUser = createMockUser({ role: 'admin' });

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: mockUser,
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: vi.fn(),
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(
        <ProtectedRoute requiredRole="admin" fallback={<div>Insufficient permissions</div>}>
          <div>Admin Only Content</div>
        </ProtectedRoute>
      );

      expect(screen.getByText('Admin Only Content')).toBeInTheDocument();
      expect(screen.queryByText('Insufficient permissions')).not.toBeInTheDocument();
    });
  });
});
