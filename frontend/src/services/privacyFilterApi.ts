/**
 * Privacy Filter API Service
 * Issue #35 Phase 6 - Frontend Dashboard
 *
 * Provides API client for:
 * - Privacy filter metrics and capabilities
 * - Live text testing
 * - Health monitoring
 * - PII types information
 */

import axios, { AxiosError } from 'axios';
import {
  PrivacyMetrics,
  LiveTestResult,
  PIIType,
  PIITypesResponse,
  PrivacyHealth,
} from '../types/privacy';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const PRIVACY_BASE_URL = `${API_BASE_URL}/privacy`;

/**
 * Extract error message from API response
 */
function extractErrorMessage(error: AxiosError, fallback: string): string {
  const data = error.response?.data as { detail?: string; message?: string; error?: { message?: string } } | undefined;

  if (data?.error?.message) {
    return data.error.message;
  }
  if (data?.detail) {
    return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
  }
  if (data?.message) {
    return data.message;
  }
  if (error.response?.statusText) {
    return error.response.statusText;
  }
  if (error.message) {
    return error.message;
  }
  return fallback;
}

class PrivacyFilterApiService {
  /**
   * Get privacy filter metrics and capabilities
   */
  async getMetrics(): Promise<PrivacyMetrics> {
    try {
      const response = await axios.get<PrivacyMetrics>(`${PRIVACY_BASE_URL}/metrics`);
      return response.data;
    } catch (error) {
      throw new Error(extractErrorMessage(error as AxiosError, 'Failed to get privacy metrics'));
    }
  }

  /**
   * Get privacy filter health status
   */
  async getHealth(): Promise<PrivacyHealth> {
    try {
      const response = await axios.get<PrivacyHealth>(`${PRIVACY_BASE_URL}/health`);
      return response.data;
    } catch (error) {
      throw new Error(extractErrorMessage(error as AxiosError, 'Failed to get health status'));
    }
  }

  /**
   * Get all supported PII types
   */
  async getPIITypes(): Promise<PIIType[]> {
    try {
      const response = await axios.get<PIITypesResponse>(`${PRIVACY_BASE_URL}/pii-types`);
      return response.data.pii_types;
    } catch (error) {
      throw new Error(extractErrorMessage(error as AxiosError, 'Failed to get PII types'));
    }
  }

  /**
   * Test privacy filter with custom text
   */
  async testText(text: string): Promise<LiveTestResult> {
    try {
      const response = await axios.post<LiveTestResult>(`${PRIVACY_BASE_URL}/test`, { text });
      return response.data;
    } catch (error) {
      throw new Error(extractErrorMessage(error as AxiosError, 'Failed to test text'));
    }
  }
}

// Export singleton instance
export const privacyFilterApi = new PrivacyFilterApiService();

// Export class for testing
export default PrivacyFilterApiService;
