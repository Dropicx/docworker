/**
 * Mock API Service
 *
 * Provides mock implementations of API services for testing.
 * All methods are vi.fn() mocks that can be configured in tests.
 */

import { vi } from 'vitest';
import {
  createMockUploadResponse,
  createMockProcessingProgress,
  createMockTranslationResult,
  createMockHealthCheck,
  createMockUploadLimits,
  createMockAvailableModels,
  createMockActiveProcessesResponse,
  createMockLanguagesResponse,
} from './testData';

/**
 * Mock implementation of ApiService
 * Each method returns a vi.fn() that can be customized in tests
 */
export const mockApiService = {
  // ==================== Upload & Processing ====================

  uploadDocument: vi.fn().mockResolvedValue(createMockUploadResponse()),

  startProcessing: vi.fn().mockResolvedValue({
    message: 'Processing started',
    processing_id: 'test-processing-id-001',
    status: 'processing',
  }),

  getProcessingStatus: vi.fn().mockResolvedValue(createMockProcessingProgress()),

  getProcessingResult: vi.fn().mockResolvedValue(createMockTranslationResult()),

  cancelProcessing: vi.fn().mockResolvedValue({
    message: 'Processing cancelled',
    processing_id: 'test-processing-id-001',
  }),

  // ==================== Health Checks ====================

  getHealth: vi.fn().mockResolvedValue(createMockHealthCheck()),

  getDetailedHealth: vi.fn().mockResolvedValue({
    status: 'healthy',
    detailed_info: {},
  }),

  checkDependencies: vi.fn().mockResolvedValue({
    status: 'healthy',
    dependencies: {},
  }),

  // ==================== Upload Info ====================

  getUploadLimits: vi.fn().mockResolvedValue(createMockUploadLimits()),

  getUploadHealth: vi.fn().mockResolvedValue({
    status: 'healthy',
  }),

  // ==================== Models & Processes ====================

  getAvailableModels: vi.fn().mockResolvedValue(createMockAvailableModels()),

  getActiveProcesses: vi.fn().mockResolvedValue(createMockActiveProcessesResponse()),

  // ==================== Languages ====================

  getAvailableLanguages: vi.fn().mockResolvedValue(createMockLanguagesResponse()),

  // ==================== Utility Methods ====================

  formatFileSize: vi.fn((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }),

  formatDuration: vi.fn((seconds: number): string => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = Math.floor(seconds % 60);
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  }),

  getStatusColor: vi.fn((status: string): string => {
    switch (status) {
      case 'pending':
        return 'status-pending';
      case 'processing':
      case 'extracting_text':
      case 'translating':
      case 'language_translating':
        return 'status-processing';
      case 'completed':
        return 'status-completed';
      case 'error':
        return 'status-error';
      case 'non_medical_content':
      case 'terminated':
        return 'status-warning';
      default:
        return 'status-pending';
    }
  }),

  getStatusText: vi.fn((status: string): string => {
    switch (status) {
      case 'pending':
        return 'Warten';
      case 'processing':
        return 'Verarbeitung';
      case 'extracting_text':
        return 'Text-Extraktion';
      case 'translating':
        return 'Vereinfachung';
      case 'language_translating':
        return 'Übersetzung';
      case 'completed':
        return 'Abgeschlossen';
      case 'error':
        return 'Fehler';
      case 'non_medical_content':
        return 'Nicht-medizinischer Inhalt';
      case 'terminated':
        return 'Gestoppt';
      default:
        return status;
    }
  }),

  validateFile: vi.fn((file: File): { valid: boolean; error?: string } => {
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `Datei zu groß. Maximum: ${mockApiService.formatFileSize(maxSize)}`,
      };
    }

    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: 'Dateityp nicht unterstützt. Erlaubt: PDF, JPEG, PNG',
      };
    }

    if (!file.name || file.name.length > 255) {
      return {
        valid: false,
        error: 'Ungültiger Dateiname',
      };
    }

    return { valid: true };
  }),
};

/**
 * Resets all mock functions to their initial state
 * Call this in beforeEach() or afterEach() to ensure clean test state
 */
export const resetApiServiceMocks = () => {
  Object.values(mockApiService).forEach(mock => {
    if (typeof mock === 'function' && 'mockClear' in mock) {
      mock.mockClear();
    }
  });
};

/**
 * Mock implementation of authApiService
 */
export const mockAuthApiService = {
  login: vi.fn().mockResolvedValue({
    access_token: 'mock-access-token',
    refresh_token: 'mock-refresh-token',
    token_type: 'Bearer',
  }),

  refreshToken: vi.fn().mockResolvedValue({
    access_token: 'mock-new-access-token',
    refresh_token: 'mock-new-refresh-token',
    token_type: 'Bearer',
  }),

  logout: vi.fn().mockResolvedValue({
    message: 'Logout successful',
  }),

  getCurrentUser: vi.fn().mockResolvedValue({
    id: 'test-user-id',
    email: 'test@example.com',
    full_name: 'Test User',
    role: 'user',
    is_active: true,
    is_verified: true,
    created_at: '2024-01-01T00:00:00Z',
  }),

  changePassword: vi.fn().mockResolvedValue({
    message: 'Password changed successfully',
  }),

  register: vi.fn().mockResolvedValue({
    message: 'Registration successful',
    user_id: 'new-user-id',
  }),

  verifyEmail: vi.fn().mockResolvedValue({
    message: 'Email verified successfully',
  }),

  requestPasswordReset: vi.fn().mockResolvedValue({
    message: 'Password reset email sent',
  }),

  resetPassword: vi.fn().mockResolvedValue({
    message: 'Password reset successful',
  }),
};

/**
 * Resets all auth mock functions
 */
export const resetAuthApiServiceMocks = () => {
  Object.values(mockAuthApiService).forEach(mock => {
    if (typeof mock === 'function' && 'mockClear' in mock) {
      mock.mockClear();
    }
  });
};

/**
 * Helper to mock API service with custom implementations
 *
 * @example
 * ```tsx
 * vi.mock('../../services/api', () => ({
 *   ApiService: mockApiServiceWith({
 *     uploadDocument: vi.fn().mockRejectedValue(new Error('Upload failed'))
 *   })
 * }));
 * ```
 */
export const mockApiServiceWith = (overrides: Partial<typeof mockApiService>) => ({
  ...mockApiService,
  ...overrides,
});

/**
 * Helper to mock auth API service with custom implementations
 */
export const mockAuthApiServiceWith = (overrides: Partial<typeof mockAuthApiService>) => ({
  ...mockAuthApiService,
  ...overrides,
});
