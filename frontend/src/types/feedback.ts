/**
 * Feedback System Types (Issue #47)
 *
 * TypeScript types for the user feedback system with GDPR data protection.
 */

// ==================== DETAILED RATINGS ====================

/**
 * Detailed ratings for specific aspects of the translation
 */
export interface DetailedRatings {
  /** Verständlichkeit (Clarity) - 1-5 */
  clarity?: number;
  /** Genauigkeit (Accuracy) - 1-5 */
  accuracy?: number;
  /** Formatierung (Formatting) - 1-5 */
  formatting?: number;
  /** Geschwindigkeit (Speed) - 1-5 */
  speed?: number;
}

// ==================== SUBMISSION ====================

/**
 * Request payload for submitting feedback
 */
export interface FeedbackSubmission {
  /** Processing job ID */
  processing_id: string;
  /** Overall rating (1-5, required) */
  overall_rating: number;
  /** Optional detailed ratings */
  detailed_ratings?: DetailedRatings;
  /** Optional text comment */
  comment?: string;
  /** Whether user consents to data usage (required) */
  data_consent_given: boolean;
}

// ==================== RESPONSES ====================

/**
 * Response after submitting feedback
 */
export interface FeedbackResponse {
  id: number;
  processing_id: string;
  overall_rating: number;
  detailed_ratings: DetailedRatings | null;
  comment: string | null;
  data_consent_given: boolean;
  submitted_at: string;
}

/**
 * Response for checking if feedback exists
 */
export interface FeedbackExistsResponse {
  exists: boolean;
  processing_id: string;
}

/**
 * Response for content cleanup
 */
export interface CleanupResponse {
  status: 'cleared' | 'skipped' | 'not_found' | 'error';
  processing_id?: string;
  reason?: string;
}

// ==================== ADMIN LIST ====================

/**
 * Feedback entry in list response
 */
export interface FeedbackEntry {
  id: number;
  processing_id: string;
  overall_rating: number;
  detailed_ratings: DetailedRatings | null;
  comment: string | null;
  data_consent_given: boolean;
  submitted_at: string;
}

/**
 * Query parameters for feedback list
 */
export interface FeedbackListQuery {
  skip?: number;
  limit?: number;
  rating_filter?: number;
  consent_filter?: boolean;
  start_date?: string;
  end_date?: string;
  sort_by?: 'submitted_at' | 'overall_rating';
  sort_order?: 'asc' | 'desc';
}

/**
 * Response for feedback list
 */
export interface FeedbackListResponse {
  entries: FeedbackEntry[];
  total: number;
  skip: number;
  limit: number;
}

// ==================== ADMIN STATISTICS ====================

/**
 * Statistics for detailed ratings
 */
export interface DetailedRatingsStats {
  clarity: number;
  accuracy: number;
  formatting: number;
  speed: number;
}

/**
 * Aggregate feedback statistics
 */
export interface FeedbackStats {
  total_feedback: number;
  average_overall_rating: number;
  rating_distribution: Record<string, number>;
  consent_rate: number;
  with_comments_count: number;
  average_detailed_ratings: DetailedRatingsStats;
}

// ==================== ADMIN DETAIL ====================

/**
 * Job data included in feedback detail (if consented)
 */
export interface JobData {
  filename: string | null;
  file_type: string | null;
  status: string | null;
  completed_at: string | null;
  processing_time_seconds: number | null;
  document_type: string | null;
  original_text?: string | null;
  translated_text?: string | null;
  language_translated_text?: string | null;
  content_available?: boolean;
}

/**
 * Detailed feedback with associated job data
 */
export interface FeedbackDetail extends FeedbackEntry {
  job_data: JobData | null;
}
