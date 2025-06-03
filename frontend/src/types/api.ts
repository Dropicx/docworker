// API Response Types
export interface UploadResponse {
  processing_id: string;
  filename: string;
  file_type: 'pdf' | 'image';
  file_size: number;
  status: ProcessingStatus;
  message: string;
}

export interface ProcessingProgress {
  processing_id: string;
  status: ProcessingStatus;
  progress_percent: number;
  current_step: string;
  message?: string;
  error?: string;
  timestamp: string;
}

export interface TranslationResult {
  processing_id: string;
  original_text: string;
  translated_text: string;
  document_type_detected: string;
  confidence_score: number;
  processing_time_seconds: number;
  timestamp: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  processing_id?: string;
  timestamp: string;
}

export interface HealthCheck {
  status: string;
  timestamp: string;
  services: Record<string, string>;
  memory_usage?: {
    rss: number;
    vms: number;
    percent: number;
    processing_store_size: number;
  };
}

// Processing Status Enum
export type ProcessingStatus = 
  | 'pending'
  | 'processing'
  | 'extracting_text'
  | 'translating'
  | 'completed'
  | 'error';

// File Types
export type FileType = 'pdf' | 'image';

// Upload Limits
export interface UploadLimits {
  max_file_size_mb: number;
  allowed_formats: string[];
  rate_limit: string;
  max_pages_pdf: number;
  min_image_size: string;
  max_image_size: string;
  processing_timeout_minutes: number;
}

// Models
export interface AvailableModels {
  connected: boolean;
  models: string[];
  recommended?: string;
  timestamp: string;
  error?: string;
}

// Active Processes
export interface ActiveProcess {
  processing_id: string;
  status: ProcessingStatus;
  progress_percent: number;
  current_step: string;
  created_at: string;
  filename?: string;
}

export interface ActiveProcessesResponse {
  active_count: number;
  processes: ActiveProcess[];
  timestamp: string;
}

// API Error
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
} 