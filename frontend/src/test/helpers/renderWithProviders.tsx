/**
 * Test Rendering Utilities
 *
 * Provides utility functions for rendering React components with required providers
 * (AuthProvider, Router, etc.) in tests.
 */

import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { ReactElement, ReactNode } from 'react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { AuthProvider, User, AuthTokens } from '../../contexts/AuthContext';
import { createMockUser, createMockAuthTokens } from './testData';

// ==================== Types ====================

export interface ProvidersOptions {
  /**
   * Initial route for MemoryRouter (use this for testing navigation)
   * If not provided, uses BrowserRouter
   */
  initialRoute?: string;

  /**
   * Initial router entries for MemoryRouter
   */
  initialEntries?: string[];

  /**
   * Mock authentication state
   */
  authState?: {
    user?: User | null;
    tokens?: AuthTokens | null;
    isLoading?: boolean;
    isAuthenticated?: boolean;
  };

  /**
   * Whether to wrap with AuthProvider (default: true)
   */
  withAuth?: boolean;
}

export interface ExtendedRenderOptions extends Omit<RenderOptions, 'wrapper'>, ProvidersOptions {}

// ==================== Provider Wrappers ====================

/**
 * Creates a wrapper component with all necessary providers
 */
function createWrapper(options: ProvidersOptions = {}) {
  const {
    initialRoute,
    initialEntries,
    withAuth = true,
  } = options;

  return function Wrapper({ children }: { children: ReactNode }) {
    // Choose router type based on options
    const RouterComponent = initialRoute || initialEntries ? MemoryRouter : BrowserRouter;
    const routerProps = initialRoute
      ? { initialEntries: [initialRoute], initialIndex: 0 }
      : initialEntries
      ? { initialEntries, initialIndex: 0 }
      : {};

    // If auth is disabled or custom auth state provided, render without AuthProvider
    if (!withAuth) {
      return <RouterComponent {...routerProps}>{children}</RouterComponent>;
    }

    // Wrap with AuthProvider
    return (
      <RouterComponent {...routerProps}>
        <AuthProvider>{children}</AuthProvider>
      </RouterComponent>
    );
  };
}

// ==================== Render Functions ====================

/**
 * Renders a component with all necessary providers
 *
 * @example
 * ```tsx
 * renderWithProviders(<MyComponent />, {
 *   initialRoute: '/dashboard',
 *   authState: {
 *     user: createMockUser(),
 *     tokens: createMockAuthTokens(),
 *     isAuthenticated: true
 *   }
 * });
 * ```
 */
export function renderWithProviders(
  ui: ReactElement,
  options: ExtendedRenderOptions = {}
): RenderResult {
  const { initialRoute, initialEntries, withAuth, ...renderOptions } = options;

  const Wrapper = createWrapper({ initialRoute, initialEntries, withAuth });

  return render(ui, {
    wrapper: Wrapper,
    ...renderOptions,
  });
}

/**
 * Renders a component with authenticated user context
 *
 * @example
 * ```tsx
 * renderWithAuth(<ProtectedComponent />, {
 *   user: createMockAdminUser()
 * });
 * ```
 */
export function renderWithAuth(
  ui: ReactElement,
  options: Omit<ExtendedRenderOptions, 'authState'> & {
    user?: User;
    tokens?: AuthTokens;
    isLoading?: boolean;
  } = {}
): RenderResult {
  const { user = createMockUser(), tokens = createMockAuthTokens(), isLoading = false, ...rest } = options;

  return renderWithProviders(ui, {
    ...rest,
    authState: {
      user,
      tokens,
      isLoading,
      isAuthenticated: true,
    },
  });
}

/**
 * Renders a component without authentication (guest user)
 *
 * @example
 * ```tsx
 * renderWithoutAuth(<LoginPage />);
 * ```
 */
export function renderWithoutAuth(
  ui: ReactElement,
  options: ExtendedRenderOptions = {}
): RenderResult {
  return renderWithProviders(ui, {
    ...options,
    authState: {
      user: null,
      tokens: null,
      isLoading: false,
      isAuthenticated: false,
    },
  });
}

/**
 * Renders a component with loading authentication state
 *
 * @example
 * ```tsx
 * renderWithAuthLoading(<SplashScreen />);
 * ```
 */
export function renderWithAuthLoading(
  ui: ReactElement,
  options: ExtendedRenderOptions = {}
): RenderResult {
  return renderWithProviders(ui, {
    ...options,
    authState: {
      user: null,
      tokens: null,
      isLoading: true,
      isAuthenticated: false,
    },
  });
}

/**
 * Renders a component with Router but without AuthProvider
 * Useful for testing components that don't need authentication
 *
 * @example
 * ```tsx
 * renderWithRouter(<Footer />, {
 *   initialRoute: '/about'
 * });
 * ```
 */
export function renderWithRouter(
  ui: ReactElement,
  options: ExtendedRenderOptions = {}
): RenderResult {
  return renderWithProviders(ui, {
    ...options,
    withAuth: false,
  });
}

// ==================== Re-exports ====================

// Re-export everything from @testing-library/react for convenience
// eslint-disable-next-line react-refresh/only-export-components
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
