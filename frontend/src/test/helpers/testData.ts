/**
 * Test Data Factory
 *
 * Factory functions for creating mock data objects used in tests.
 * All factories accept an optional overrides parameter to customize the generated data.
 */

import {
  UploadResponse,
  ProcessingProgress,
  TranslationResult,
  SupportedLanguage,
  AvailableLanguagesResponse,
  ErrorResponse,
  HealthCheck,
  ProcessingStatus,
  ActiveProcess,
  ActiveProcessesResponse,
  UploadLimits,
  AvailableModels,
} from '../../types/api';
import { User, AuthTokens } from '../../contexts/AuthContext';

// ==================== Auth Related ====================

export const createMockUser = (overrides?: Partial<User>): User => ({
  id: 'test-user-id-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'user',
  is_active: true,
  is_verified: true,
  created_at: '2024-01-01T00:00:00Z',
  last_login_at: '2024-01-15T10:30:00Z',
  ...overrides,
});

export const createMockAdminUser = (overrides?: Partial<User>): User =>
  createMockUser({
    id: 'admin-user-id-456',
    email: 'admin@example.com',
    full_name: 'Admin User',
    role: 'admin',
    ...overrides,
  });

export const createMockAuthTokens = (overrides?: Partial<AuthTokens>): AuthTokens => ({
  access_token: 'mock-access-token-abc123xyz',
  refresh_token: 'mock-refresh-token-def456uvw',
  token_type: 'Bearer',
  ...overrides,
});

// ==================== Upload & Processing ====================

export const createMockUploadResponse = (
  overrides?: Partial<UploadResponse>
): UploadResponse => ({
  processing_id: 'test-processing-id-001',
  filename: 'test-document.pdf',
  file_type: 'pdf',
  file_size: 1024000, // 1MB
  status: 'pending',
  message: 'Upload successful',
  ...overrides,
});

export const createMockProcessingProgress = (
  overrides?: Partial<ProcessingProgress>
): ProcessingProgress => ({
  processing_id: 'test-processing-id-001',
  status: 'processing',
  progress_percent: 50,
  current_step: 'TRANSLATION',
  message: 'Processing document...',
  timestamp: new Date().toISOString(),
  ...overrides,
});

export const createMockTranslationResult = (
  overrides?: Partial<TranslationResult>
): TranslationResult => ({
  processing_id: 'test-processing-id-001',
  original_text: '**Original German Medical Text**\n\nPatient has diabetes.',
  translated_text:
    '**Simplified Translation**\n\nThe patient has been diagnosed with diabetes mellitus.',
  language_translated_text: '**English Translation**\n\nPatient has diabetes.',
  target_language: 'en',
  document_type_detected: 'ARZTBRIEF',
  confidence_score: 0.95,
  language_confidence_score: 0.92,
  processing_time_seconds: 12.5,
  timestamp: new Date().toISOString(),
  ...overrides,
});

export const createMockTerminatedResult = (
  overrides?: Partial<TranslationResult>
): TranslationResult =>
  createMockTranslationResult({
    terminated: true,
    termination_step: 'MEDICAL_VALIDATION',
    termination_reason: 'non_medical_content',
    termination_message: 'Document does not contain medical content',
    matched_value: 'shopping list',
    ...overrides,
  });

// ==================== Languages ====================

export const createMockLanguage = (
  overrides?: Partial<SupportedLanguage>
): SupportedLanguage => ({
  code: 'en',
  name: 'English',
  popular: true,
  ...overrides,
});

export const createMockLanguages = (): SupportedLanguage[] => [
  { code: 'en', name: 'English', popular: true },
  { code: 'fr', name: 'Français (French)', popular: true },
  { code: 'es', name: 'Español (Spanish)', popular: true },
  { code: 'it', name: 'Italiano (Italian)', popular: true },
  { code: 'pt', name: 'Português (Portuguese)', popular: false },
  { code: 'nl', name: 'Nederlands (Dutch)', popular: false },
  { code: 'pl', name: 'Polski (Polish)', popular: false },
];

export const createMockLanguagesResponse = (
  overrides?: Partial<AvailableLanguagesResponse>
): AvailableLanguagesResponse => ({
  languages: createMockLanguages(),
  total_count: 7,
  popular_count: 4,
  timestamp: new Date().toISOString(),
  ...overrides,
});

// ==================== Errors ====================

export const createMockErrorResponse = (overrides?: Partial<ErrorResponse>): ErrorResponse => ({
  error: 'ValidationError',
  message: 'Invalid file format',
  timestamp: new Date().toISOString(),
  ...overrides,
});

// ==================== Health & Status ====================

export const createMockHealthCheck = (overrides?: Partial<HealthCheck>): HealthCheck => ({
  status: 'healthy',
  timestamp: new Date().toISOString(),
  services: {
    api: 'healthy',
    database: 'healthy',
    redis: 'healthy',
    celery: 'healthy',
  },
  memory_usage: {
    rss: 150000000,
    vms: 200000000,
    percent: 35.5,
    processing_store_size: 5,
  },
  ...overrides,
});

export const createMockActiveProcess = (
  overrides?: Partial<ActiveProcess>
): ActiveProcess => ({
  processing_id: 'active-process-001',
  status: 'processing',
  progress_percent: 45,
  current_step: 'TRANSLATION',
  created_at: new Date().toISOString(),
  filename: 'document.pdf',
  ...overrides,
});

export const createMockActiveProcessesResponse = (
  overrides?: Partial<ActiveProcessesResponse>
): ActiveProcessesResponse => ({
  active_count: 2,
  processes: [
    createMockActiveProcess({ processing_id: 'process-1', progress_percent: 30 }),
    createMockActiveProcess({ processing_id: 'process-2', progress_percent: 60 }),
  ],
  timestamp: new Date().toISOString(),
  ...overrides,
});

// ==================== Configuration ====================

export const createMockUploadLimits = (overrides?: Partial<UploadLimits>): UploadLimits => ({
  max_file_size_mb: 50,
  allowed_formats: ['pdf', 'jpg', 'jpeg', 'png'],
  rate_limit: '10 per minute',
  max_pages_pdf: 100,
  min_image_size: '800x600',
  max_image_size: '4000x4000',
  processing_timeout_minutes: 30,
  ...overrides,
});

export const createMockAvailableModels = (
  overrides?: Partial<AvailableModels>
): AvailableModels => ({
  connected: true,
  models: ['Meta-Llama-3_3-70B-Instruct', 'Mistral-Nemo-Instruct-2407'],
  recommended: 'Meta-Llama-3_3-70B-Instruct',
  timestamp: new Date().toISOString(),
  ...overrides,
});

// ==================== File Mocks ====================

/**
 * Creates a mock File object for testing file uploads
 */
export const createMockFile = (
  name: string = 'test-document.pdf',
  size: number = 1024000,
  type: string = 'application/pdf',
  content: string = 'Mock PDF content'
): File => {
  const blob = new Blob([content], { type });
  const file = new File([blob], name, { type });

  // Add size property (File inherits from Blob which has size)
  Object.defineProperty(file, 'size', { value: size });

  return file;
};

/**
 * Creates multiple mock files for multi-file upload testing
 */
export const createMockFiles = (count: number = 3): File[] => {
  return Array.from({ length: count }, (_, i) =>
    createMockFile(`document-${i + 1}.pdf`, 1024000 * (i + 1))
  );
};

/**
 * Creates a mock image file
 */
export const createMockImageFile = (
  name: string = 'test-image.jpg',
  size: number = 512000
): File => {
  return createMockFile(name, size, 'image/jpeg', 'Mock JPEG content');
};

// ==================== Status Helpers ====================

/**
 * Creates a sequence of processing statuses for testing polling
 */
export const createMockProcessingSequence = (): ProcessingProgress[] => {
  const baseProgress: Omit<ProcessingProgress, 'status' | 'progress_percent' | 'current_step'> = {
    processing_id: 'test-processing-id-001',
    message: 'Processing...',
    timestamp: new Date().toISOString(),
  };

  const statuses: Array<{
    status: ProcessingStatus;
    progress: number;
    step: string;
  }> = [
    { status: 'pending', progress: 0, step: 'PENDING' },
    { status: 'extracting_text', progress: 20, step: 'TEXT_EXTRACTION' },
    { status: 'processing', progress: 40, step: 'MEDICAL_VALIDATION' },
    { status: 'translating', progress: 60, step: 'TRANSLATION' },
    { status: 'language_translating', progress: 80, step: 'LANGUAGE_TRANSLATION' },
    { status: 'completed', progress: 100, step: 'FINAL_CHECK' },
  ];

  return statuses.map(({ status, progress, step }) => ({
    ...baseProgress,
    status,
    progress_percent: progress,
    current_step: step,
  }));
};

// ==================== Date Helpers ====================

/**
 * Creates an ISO timestamp for a relative time
 */
export const createMockTimestamp = (minutesAgo: number = 0): string => {
  const date = new Date();
  date.setMinutes(date.getMinutes() - minutesAgo);
  return date.toISOString();
};
