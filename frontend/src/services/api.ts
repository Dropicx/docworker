import axios, { AxiosResponse } from 'axios';
import {
  UploadResponse,
  ProcessingProgress,
  TranslationResult,
  HealthCheck,
  UploadLimits,
  AvailableModels,
  ActiveProcessesResponse,
  ProcessingOptions,
  AvailableLanguagesResponse,
  ApiError
} from '../types/api';

// Base API configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes timeout for processing
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use((config) => {
  console.log(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error(`❌ API Error: ${error.response?.status} ${error.config?.url}`, error.response?.data);
    
    const message = error.response?.data?.detail || 
                   error.response?.data?.message || 
                   error.message || 
                   'Unknown API error';
    
    throw new ApiError(
      message,
      error.response?.status || 500,
      error.response?.data
    );
  }
);

export class ApiService {
  // Upload document
  static async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    // Use shorter timeout for upload (30 seconds should be enough even for 50MB on mobile)
    const response: AxiosResponse<UploadResponse> = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 30000, // 30 seconds timeout for upload specifically
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
    const response: AxiosResponse<ProcessingProgress> = await api.get(`/process/${processingId}/status`);
    return response.data;
  }

  // Get processing result
  static async getProcessingResult(processingId: string): Promise<TranslationResult> {
    const response: AxiosResponse<TranslationResult> = await api.get(`/process/${processingId}/result`);
    return response.data;
  }

  // Cancel processing
  static async cancelProcessing(processingId: string): Promise<{ message: string; processing_id: string }> {
    const response = await api.delete(`/upload/${processingId}`);
    return response.data;
  }

  // Health checks
  static async getHealth(): Promise<HealthCheck> {
    const response: AxiosResponse<HealthCheck> = await api.get('/health');
    return response.data;
  }

  static async getDetailedHealth(): Promise<any> {
    const response = await api.get('/health/detailed');
    return response.data;
  }

  static async checkDependencies(): Promise<any> {
    const response = await api.get('/health/dependencies');
    return response.data;
  }

  // Upload limits and info
  static async getUploadLimits(): Promise<UploadLimits> {
    const response: AxiosResponse<UploadLimits> = await api.get('/upload/limits');
    return response.data;
  }

  static async getUploadHealth(): Promise<any> {
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
        error: `Datei zu groß. Maximum: ${this.formatFileSize(maxSize)}`
      };
    }

    // File type check
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: 'Dateityp nicht unterstützt. Erlaubt: PDF, JPEG, PNG'
      };
    }

    // File name check
    if (!file.name || file.name.length > 255) {
      return {
        valid: false,
        error: 'Ungültiger Dateiname'
      };
    }

    return { valid: true };
  }
}

export default ApiService; 