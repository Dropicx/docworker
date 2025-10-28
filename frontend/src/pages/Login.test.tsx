/**
 * Login Component Tests
 *
 * Comprehensive test suite covering:
 * - Rendering and initial state
 * - Form input handling (email, password)
 * - Password visibility toggle
 * - Form validation and submission
 * - Loading states (auth loading, form loading)
 * - Error handling and display
 * - Navigation (back to home, redirect after login)
 * - Auto-redirect when already authenticated
 * - Auth logout event listener
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter, userEvent } from '../test/helpers/renderWithProviders';
import { createMockUser } from '../test/helpers/testData';
import Login from './Login';
import * as AuthContext from '../contexts/AuthContext';

// Mock the entire AuthContext module
vi.mock('../contexts/AuthContext', async () => {
  const actual = await vi.importActual('../contexts/AuthContext');
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

describe('Login Component', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== Rendering and Initial State Tests ====================

  describe('Rendering and Initial State', () => {
    it('should render login form with all elements', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      expect(screen.getByText('Admin-Anmeldung')).toBeInTheDocument();
      expect(screen.getByLabelText('E-Mail-Adresse')).toBeInTheDocument();
      expect(screen.getByLabelText('Passwort')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Anmelden/i })).toBeInTheDocument();
      expect(screen.getByText('← Zurück zur Hauptseite')).toBeInTheDocument();
    });

    it('should render HealthLingo header', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      expect(screen.getByText('HealthLingo')).toBeInTheDocument();
      expect(screen.getByText('Medizinische Dokumente verstehen')).toBeInTheDocument();
    });

    it('should render info card about no access', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      expect(screen.getByText('Kein Zugang?')).toBeInTheDocument();
      expect(
        screen.getByText('Kontaktieren Sie Ihren Administrator, um ein Konto zu erstellen.')
      ).toBeInTheDocument();
    });

    it('should have submit button disabled initially when fields are empty', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const submitButton = screen.getByRole('button', { name: /Anmelden/i });
      expect(submitButton).toBeDisabled();
    });
  });

  // ==================== Auth Loading State Tests ====================

  describe('Auth Loading State', () => {
    it('should show loading spinner when auth is loading', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: true,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      expect(screen.getByText('Lade...')).toBeInTheDocument();
      expect(screen.queryByText('Admin-Anmeldung')).not.toBeInTheDocument();
    });

    it('should show spinner icon in auth loading state', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: true,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      const { container } = renderWithRouter(<Login />);

      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  // ==================== Form Input Handling Tests ====================

  describe('Form Input Handling', () => {
    it('should update email input when typing', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse') as HTMLInputElement;
      await user.type(emailInput, 'test@example.com');

      expect(emailInput.value).toBe('test@example.com');
    });

    it('should update password input when typing', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const passwordInput = screen.getByLabelText('Passwort') as HTMLInputElement;
      await user.type(passwordInput, 'password123');

      expect(passwordInput.value).toBe('password123');
    });

    it('should enable submit button when both fields are filled', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      expect(submitButton).toBeDisabled();

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');

      expect(submitButton).not.toBeDisabled();
    });

    it('should have email input with correct type', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse') as HTMLInputElement;
      expect(emailInput.type).toBe('email');
    });
  });

  // ==================== Password Visibility Toggle Tests ====================

  describe('Password Visibility Toggle', () => {
    it('should hide password by default', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const passwordInput = screen.getByLabelText('Passwort') as HTMLInputElement;
      expect(passwordInput.type).toBe('password');
    });

    it('should show password when eye icon clicked', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const passwordInput = screen.getByLabelText('Passwort') as HTMLInputElement;
      const toggleButton = passwordInput.nextElementSibling as HTMLButtonElement;

      await user.click(toggleButton);

      expect(passwordInput.type).toBe('text');
    });

    it('should toggle password visibility multiple times', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const passwordInput = screen.getByLabelText('Passwort') as HTMLInputElement;
      const toggleButton = passwordInput.nextElementSibling as HTMLButtonElement;

      expect(passwordInput.type).toBe('password');

      await user.click(toggleButton);
      expect(passwordInput.type).toBe('text');

      await user.click(toggleButton);
      expect(passwordInput.type).toBe('password');
    });
  });

  // ==================== Form Submission Tests ====================

  describe('Form Submission', () => {
    it('should call login with correct credentials on submit', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockResolvedValue(undefined);

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'admin@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      expect(mockLogin).toHaveBeenCalledWith('admin@example.com', 'password123');
      expect(mockLogin).toHaveBeenCalledTimes(1);
    });

    it('should show loading state during submission', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      // Mock login to be slow
      mockLogin.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'admin@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Anmeldung...')).toBeInTheDocument();
      });
    });

    it('should disable form inputs during submission', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'admin@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(emailInput).toBeDisabled();
        expect(passwordInput).toBeDisabled();
        expect(submitButton).toBeDisabled();
      });
    });

    it('should prevent form submission when already submitting', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'admin@example.com');
      await user.type(passwordInput, 'password123');

      // Try to submit twice
      await user.click(submitButton);
      await user.click(submitButton);

      expect(mockLogin).toHaveBeenCalledTimes(1);
    });
  });

  // ==================== Error Handling Tests ====================

  describe('Error Handling', () => {
    it('should display error message when login fails', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockRejectedValue(new Error('Invalid credentials'));

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'wrong@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
      });
    });

    it('should show generic error message when error is not an Error instance', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockRejectedValue('Network error');

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Anmeldung fehlgeschlagen')).toBeInTheDocument();
      });
    });

    it('should show AlertCircle icon with error message', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockRejectedValue(new Error('Login failed'));

      const { container } = renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        const alertIcon = container.querySelector('.text-error-600');
        expect(alertIcon).toBeInTheDocument();
      });
    });

    it('should clear previous error when submitting again', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      // First attempt fails
      mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'wrong@example.com');
      await user.type(passwordInput, 'wrongpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
      });

      // Second attempt should clear error
      mockLogin.mockResolvedValue(undefined);

      await user.clear(emailInput);
      await user.clear(passwordInput);
      await user.type(emailInput, 'correct@example.com');
      await user.type(passwordInput, 'correctpassword');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText('Invalid credentials')).not.toBeInTheDocument();
      });
    });
  });

  // ==================== Navigation Tests ====================

  describe('Navigation', () => {
    it('should render clickable HealthLingo header button', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const headerButton = screen.getByText('HealthLingo').closest('button');
      expect(headerButton).toBeInTheDocument();
      await user.click(headerButton!);
      // Navigation is handled by react-router-dom
    });

    it('should render clickable back button', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      const backButton = screen.getByText('← Zurück zur Hauptseite');
      expect(backButton).toBeInTheDocument();
      await user.click(backButton);
      // Navigation is handled by react-router-dom
    });

    it('should disable back button during form submission', async () => {
      const user = userEvent.setup();

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      mockLogin.mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 1000))
      );

      renderWithRouter(<Login />);

      const emailInput = screen.getByLabelText('E-Mail-Adresse');
      const passwordInput = screen.getByLabelText('Passwort');
      const submitButton = screen.getByRole('button', { name: /Anmelden/i });

      await user.type(emailInput, 'test@example.com');
      await user.type(passwordInput, 'password123');
      await user.click(submitButton);

      await waitFor(() => {
        const backButton = screen.getByText('← Zurück zur Hauptseite');
        expect(backButton).toBeDisabled();
      });
    });
  });

  // ==================== Auto-Redirect Tests ====================

  describe('Auto-Redirect When Authenticated', () => {
    it('should not render login form when already authenticated', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: createMockUser(),
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      // Should not render login form when authenticated
      // The Navigate component will handle the redirect
      expect(screen.queryByLabelText('E-Mail-Adresse')).not.toBeInTheDocument();
    });

    it('should show login form when auth is still loading', () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: true,
        user: createMockUser(),
        tokens: { access_token: 'token', refresh_token: 'refresh', token_type: 'Bearer' },
        isLoading: true,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      // Should show loading state, not login form
      expect(screen.getByText('Lade...')).toBeInTheDocument();
      expect(screen.queryByLabelText('E-Mail-Adresse')).not.toBeInTheDocument();
    });
  });

  // ==================== Auth Logout Event Tests ====================

  describe('Auth Logout Event Listener', () => {
    it('should show session expired message on auth:logout event', async () => {
      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      renderWithRouter(<Login />);

      // Dispatch logout event
      window.dispatchEvent(new Event('auth:logout'));

      await waitFor(() => {
        expect(
          screen.getByText('Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.')
        ).toBeInTheDocument();
      });
    });

    it('should add and remove event listener correctly', () => {
      const addEventListenerSpy = vi.spyOn(window, 'addEventListener');
      const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener');

      vi.mocked(AuthContext.useAuth).mockReturnValue({
        isAuthenticated: false,
        user: null,
        tokens: null,
        isLoading: false,
        login: mockLogin,
        logout: vi.fn(),
        refreshToken: vi.fn(),
        updateUser: vi.fn(),
      });

      const { unmount } = renderWithRouter(<Login />);

      expect(addEventListenerSpy).toHaveBeenCalledWith('auth:logout', expect.any(Function));

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('auth:logout', expect.any(Function));

      addEventListenerSpy.mockRestore();
      removeEventListenerSpy.mockRestore();
    });
  });
});
