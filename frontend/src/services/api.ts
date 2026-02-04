import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import {
  UploadResponse,
  ProcessingProgress,
  TranslationResult,
  GuidelinesResponse,
  HealthCheck,
  UploadLimits,
  AvailableModels,
  ActiveProcessesResponse,
  ProcessingOptions,
  AvailableLanguagesResponse,
  ApiError,
} from '../types/api';

// Base API configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes timeout for processing
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
});

// Request interceptor for authentication and logging
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  // Add authentication header if token exists
  const storedTokens = localStorage.getItem('auth_tokens');
  if (storedTokens) {
    try {
      const tokens = JSON.parse(storedTokens);
      if (tokens.access_token) {
        config.headers.Authorization = `Bearer ${tokens.access_token}`;
      }
    } catch (error) {
      console.error('Error parsing stored tokens:', error);
    }
  }

  // Log requests in development only
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.log(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
  }
  return config;
});

// Response interceptor for error handling and token refresh
api.interceptors.response.use(
  response => {
    // Log responses in development only
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    }
    return response;
  },
  async error => {
    // Log errors in development, or always log 5xx errors
    if (import.meta.env.DEV || error.response?.status >= 500) {
      console.error(
        `❌ API Error: ${error.response?.status} ${error.config?.url}`,
        error.response?.data
      );
    }

    // Handle 401 Unauthorized - try to refresh token
    if (error.response?.status === 401 && !error.config._retry) {
      const storedTokens = localStorage.getItem('auth_tokens');
      if (storedTokens) {
        try {
          const tokens = JSON.parse(storedTokens);
          if (tokens.refresh_token) {
            // Try to refresh the token
            const refreshResponse = await axios.post(
              `${API_BASE_URL}/auth/refresh`,
              {
                refresh_token: tokens.refresh_token,
              },
              {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
              }
            );

            const newTokens = {
              ...tokens,
              access_token: refreshResponse.data.access_token,
              refresh_token: refreshResponse.data.refresh_token,
            };

            // Update stored tokens
            localStorage.setItem('auth_tokens', JSON.stringify(newTokens));

            // Retry the original request with new token
            error.config.headers.Authorization = `Bearer ${newTokens.access_token}`;
            error.config._retry = true;
            return api.request(error.config);
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          // If refresh fails, clear tokens and redirect to login
          localStorage.removeItem('auth_tokens');
          localStorage.removeItem('auth_user');
          // Dispatch custom event to notify auth context
          window.dispatchEvent(new CustomEvent('auth:logout'));
        }
      }
    }

    // Extract error message - handle both string and object detail formats
    let message = 'Unknown API error';
    const detail = error.response?.data?.detail;

    if (typeof detail === 'string') {
      // Simple string error
      message = detail;
    } else if (typeof detail === 'object' && detail !== null && 'message' in detail) {
      // Structured error (like quality gate) - extract message from nested object
      message = (detail as { message: string }).message;
    } else {
      // Fallback to other message fields
      message = error.response?.data?.message || error.message || 'Unknown API error';
    }

    throw new ApiError(message, error.response?.status || 500, error.response?.data);
  }
);

export class ApiService {
  // Upload document
  static async uploadDocument(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Upload timeout - needs to account for file upload + quality analysis
    // 60 seconds allows for large files over slower connections
    const response: AxiosResponse<UploadResponse> = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 60000, // 60 seconds timeout (upload + quality gate analysis)
      onUploadProgress: e => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded * 100) / e.total));
        }
      },
    });

    return response.data;
  }

  // Start processing with optional language
  static async startProcessing(
    processingId: string,
    options?: ProcessingOptions
  ): Promise<{ message: string; processing_id: string; status: string; target_language?: string }> {
    const response = await api.post(`/process/${processingId}`, options || {});
    return response.data;
  }

  // Get processing status
  static async getProcessingStatus(processingId: string): Promise<ProcessingProgress> {
    const response: AxiosResponse<ProcessingProgress> = await api.get(
      `/process/${processingId}/status`
    );
    return response.data;
  }

  // Get processing result
  static async getProcessingResult(processingId: string): Promise<TranslationResult> {
    const response: AxiosResponse<TranslationResult> = await api.get(
      `/process/${processingId}/result`
    );
    return response.data;
  }

  // Get AWMF guideline recommendations
  static async getGuidelines(
    processingId: string,
    targetLanguage: string = 'en'
  ): Promise<GuidelinesResponse> {
    const response: AxiosResponse<GuidelinesResponse> = await api.get(
      `/process/${processingId}/guidelines`,
      {
        params: { target_language: targetLanguage },
        timeout: 120000, // 2 minutes (Dify RAG can take up to 90s)
      }
    );
    return response.data;
  }

  // Cancel processing
  static async cancelProcessing(
    processingId: string
  ): Promise<{ message: string; processing_id: string }> {
    const response = await api.delete(`/upload/${processingId}`);
    return response.data;
  }

  // Health checks
  static async getHealth(): Promise<HealthCheck> {
    const response: AxiosResponse<HealthCheck> = await api.get('/health');
    return response.data;
  }

  static async getDetailedHealth(): Promise<unknown> {
    const response = await api.get('/health/detailed');
    return response.data;
  }

  static async checkDependencies(): Promise<unknown> {
    const response = await api.get('/health/dependencies');
    return response.data;
  }

  // Upload limits and info
  static async getUploadLimits(): Promise<UploadLimits> {
    const response: AxiosResponse<UploadLimits> = await api.get('/upload/limits');
    return response.data;
  }

  static async getUploadHealth(): Promise<unknown> {
    const response = await api.get('/upload/health');
    return response.data;
  }

  // Models and processing info
  static async getAvailableModels(): Promise<AvailableModels> {
    const response: AxiosResponse<AvailableModels> = await api.get('/process/models');
    return response.data;
  }

  static async getActiveProcesses(): Promise<ActiveProcessesResponse> {
    const response: AxiosResponse<ActiveProcessesResponse> = await api.get('/process/active');
    return response.data;
  }

  // Language support
  static async getAvailableLanguages(): Promise<AvailableLanguagesResponse> {
    const response: AxiosResponse<AvailableLanguagesResponse> = await api.get('/process/languages');
    return response.data;
  }

  // Utility methods
  static formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  static formatDuration(seconds: number): string {
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
  }

  static getStatusColor(status: string): string {
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
  }

  static getStatusText(status: string): string {
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
  }

  static validateFile(file: File): { valid: boolean; error?: string } {
    // File size check (50MB - optimized for phone photos)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `Datei zu groß. Maximum: ${this.formatFileSize(maxSize)}`,
      };
    }

    // File type check
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: 'Dateityp nicht unterstützt. Erlaubt: PDF, JPEG, PNG',
      };
    }

    // File name check
    if (!file.name || file.name.length > 255) {
      return {
        valid: false,
        error: 'Ungültiger Dateiname',
      };
    }

    return { valid: true };
  }
}

export default ApiService;
