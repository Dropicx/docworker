/**
 * Cost Statistics API Service
 * Provides methods to fetch cost statistics data from the backend (Issue #51)
 */

import type {
  CostOverview,
  CostBreakdown,
  ProcessingJobsResponse,
  ProcessingJobDetail,
  ProcessingJobsQuery,
  FeedbackAnalysisCost,
} from '../types/cost';

const API_BASE = '/api/costs';

class CostApiService {
  private token: string | null = null;

  /**
   * Update the authentication token
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

  /**
   * Build URL with optional date query parameters
   */
  private buildDateUrl(endpoint: string, startDate?: string, endDate?: string): string {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const queryString = params.toString();
    return queryString ? `${API_BASE}${endpoint}?${queryString}` : `${API_BASE}${endpoint}`;
  }

  /**
   * Get cost overview statistics
   * @param startDate - Optional start date (ISO string)
   * @param endDate - Optional end date (ISO string)
   */
  async getOverview(startDate?: string, endDate?: string): Promise<CostOverview> {
    const url = this.buildDateUrl('/overview', startDate, endDate);
    const response = await fetch(url, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<CostOverview>(response);
  }

  /**
   * Get cost breakdown by model and pipeline step
   * @param startDate - Optional start date (ISO string)
   * @param endDate - Optional end date (ISO string)
   */
  async getBreakdown(startDate?: string, endDate?: string): Promise<CostBreakdown> {
    const url = this.buildDateUrl('/breakdown', startDate, endDate);
    const response = await fetch(url, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<CostBreakdown>(response);
  }

  /**
   * Get paginated list of processing jobs with costs
   * @param params - Query parameters for pagination, sorting, and search
   */
  async getProcessingJobs(params: ProcessingJobsQuery = {}): Promise<ProcessingJobsResponse> {
    const queryParams = new URLSearchParams();
    if (params.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params.sort_order) queryParams.append('sort_order', params.sort_order);
    if (params.search) queryParams.append('search', params.search);

    const queryString = queryParams.toString();
    const url = queryString
      ? `${API_BASE}/processing-jobs?${queryString}`
      : `${API_BASE}/processing-jobs`;

    const response = await fetch(url, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<ProcessingJobsResponse>(response);
  }

  /**
   * Get detailed cost information for a specific processing job
   * @param processingId - The processing job ID
   */
  async getProcessingJobDetail(processingId: string): Promise<ProcessingJobDetail> {
    const response = await fetch(`${API_BASE}/processing-jobs/${processingId}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<ProcessingJobDetail>(response);
  }

  /**
   * Get cost statistics for feedback AI analysis
   * @param startDate - Optional start date (ISO string)
   * @param endDate - Optional end date (ISO string)
   */
  async getFeedbackAnalysisCosts(
    startDate?: string,
    endDate?: string
  ): Promise<FeedbackAnalysisCost> {
    const url = this.buildDateUrl('/feedback-analysis', startDate, endDate);
    const response = await fetch(url, {
      headers: this.getHeaders(),
    });
    return this.handleResponse<FeedbackAnalysisCost>(response);
  }
}

export const costApi = new CostApiService();
