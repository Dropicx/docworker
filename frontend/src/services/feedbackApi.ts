/**
 * Feedback API Service (Issue #47)
 *
 * Provides methods to interact with the feedback backend API.
 */

import type {
  FeedbackSubmission,
  FeedbackResponse,
  FeedbackExistsResponse,
  CleanupResponse,
  FeedbackListQuery,
  FeedbackListResponse,
  FeedbackStats,
  FeedbackDetail,
} from '../types/feedback';

const API_BASE = '/api/feedback';

class FeedbackApiService {
  private token: string | null = null;

  /**
   * Update the authentication token (for admin endpoints)
   */
  updateToken(token: string): void {
    this.token = token;
  }

  /**
   * Get headers for authenticated requests
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  /**
   * Handle API response and extract data or throw error
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  // ==================== PUBLIC ENDPOINTS ====================

  /**
   * Submit feedback for a translation
   * @param data - Feedback submission data
   */
  async submitFeedback(data: FeedbackSubmission): Promise<FeedbackResponse> {
    const response = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(data),
    });
    return this.handleResponse<FeedbackResponse>(response);
  }

  /**
   * Check if feedback exists for a processing ID
   * @param processingId - The processing job ID
   */
  async checkFeedbackExists(processingId: string): Promise<boolean> {
    const response = await fetch(`${API_BASE}/${processingId}`);
    const data = await this.handleResponse<FeedbackExistsResponse>(response);
    return data.exists;
  }

  /**
   * Cleanup content for a processing job (called when user leaves)
   * Uses sendBeacon for reliability on page close
   * Note: Renamed endpoint from "cleanup" to "clear" to avoid ad blocker blocking
   * @param processingId - The processing job ID
   */
  cleanupContent(processingId: string): void {
    // Use sendBeacon for reliable delivery on page unload
    // Note: Using "clear" instead of "cleanup" to avoid ad blocker blocking
    const url = `${API_BASE}/clear/${processingId}`;
    if (navigator.sendBeacon) {
      const blob = new Blob([], { type: 'application/json' });
      navigator.sendBeacon(url, blob);
    } else {
      // Fallback for older browsers
      fetch(url, {
        method: 'POST',
        keepalive: true,
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
      }).catch(() => {
        // Ignore errors - cleanup is best effort
      });
    }
  }

  /**
   * Cleanup content with async response (for explicit cleanup)
   * @param processingId - The processing job ID
   */
  async cleanupContentAsync(processingId: string): Promise<CleanupResponse> {
    const response = await fetch(`${API_BASE}/cleanup/${processingId}`, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    return this.handleResponse<CleanupResponse>(response);
  }

  // ==================== ADMIN ENDPOINTS ====================

  /**
   * Get list of feedback entries (admin only)
   * @param params - Query parameters
   */
  async listFeedback(params: FeedbackListQuery = {}): Promise<FeedbackListResponse> {
    const queryParams = new URLSearchParams();
    if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params.rating_filter !== undefined)
      queryParams.append('rating_filter', params.rating_filter.toString());
    if (params.consent_filter !== undefined)
      queryParams.append('consent_filter', params.consent_filter.toString());
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params.sort_order) queryParams.append('sort_order', params.sort_order);

    const queryString = queryParams.toString();
    const url = queryString ? `${API_BASE}/admin/list?${queryString}` : `${API_BASE}/admin/list`;

    const response = await fetch(url, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<FeedbackListResponse>(response);
  }

  /**
   * Get feedback statistics (admin only)
   * @param startDate - Optional start date filter
   */
  async getStats(startDate?: string): Promise<FeedbackStats> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);

    const queryString = params.toString();
    const url = queryString ? `${API_BASE}/admin/stats?${queryString}` : `${API_BASE}/admin/stats`;

    const response = await fetch(url, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<FeedbackStats>(response);
  }

  /**
   * Get detailed feedback with job data (admin only)
   * @param feedbackId - Feedback entry ID
   */
  async getFeedbackDetail(feedbackId: number): Promise<FeedbackDetail> {
    const response = await fetch(`${API_BASE}/admin/${feedbackId}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<FeedbackDetail>(response);
  }
}

export const feedbackApi = new FeedbackApiService();
