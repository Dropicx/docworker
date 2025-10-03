/**
 * Modular Pipeline API Service
 *
 * Provides API client for managing:
 * - OCR engine configuration
 * - Dynamic pipeline steps
 * - Available AI models
 */

import axios, { AxiosError } from 'axios';
import {
  OCRConfiguration,
  OCRConfigRequest,
  PipelineStep,
  PipelineStepRequest,
  AIModel,
  EngineStatus,
  EngineStatusMap,
  StepReorderRequest,
  StepReorderResponse,
  OCREngineEnum
} from '../types/pipeline';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const PIPELINE_BASE_URL = `${API_BASE_URL}/pipeline`;

// Token management (shared with settings service)
const TOKEN_KEY = 'settings_auth_token';

class PipelineApiService {
  private token: string | null = null;

  constructor() {
    // Load token from localStorage on initialization
    this.token = localStorage.getItem(TOKEN_KEY);
  }

  // Set authorization header if token exists
  private getAuthHeaders() {
    if (!this.token) {
      throw new Error('Not authenticated');
    }
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }

  // Check if authenticated
  public isAuthenticated(): boolean {
    return !!this.token;
  }

  // Update token (called when settings service authenticates)
  public updateToken(token: string | null) {
    this.token = token;
  }

  // ==================== OCR CONFIGURATION ====================

  /**
   * Get current OCR configuration
   */
  async getOCRConfig(): Promise<OCRConfiguration> {
    try {
      const response = await axios.get<OCRConfiguration>(
        `${PIPELINE_BASE_URL}/ocr-config`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get OCR configuration'
      );
    }
  }

  /**
   * Update OCR configuration
   */
  async updateOCRConfig(config: OCRConfigRequest): Promise<OCRConfiguration> {
    try {
      const response = await axios.put<OCRConfiguration>(
        `${PIPELINE_BASE_URL}/ocr-config`,
        config,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to update OCR configuration'
      );
    }
  }

  /**
   * Get all available OCR engines
   */
  async getAvailableEngines(): Promise<EngineStatusMap> {
    try {
      const response = await axios.get<EngineStatusMap>(
        `${PIPELINE_BASE_URL}/ocr-engines`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get available engines'
      );
    }
  }

  /**
   * Get status of a specific OCR engine
   */
  async getEngineStatus(engine: OCREngineEnum): Promise<EngineStatus> {
    try {
      const response = await axios.get<EngineStatus>(
        `${PIPELINE_BASE_URL}/ocr-engines/${engine}`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || `Failed to get ${engine} status`
      );
    }
  }

  // ==================== PIPELINE STEPS ====================

  /**
   * Get all pipeline steps
   */
  async getAllSteps(): Promise<PipelineStep[]> {
    try {
      const response = await axios.get<PipelineStep[]>(
        `${PIPELINE_BASE_URL}/steps`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get pipeline steps'
      );
    }
  }

  /**
   * Get a single pipeline step by ID
   */
  async getStep(stepId: number): Promise<PipelineStep> {
    try {
      const response = await axios.get<PipelineStep>(
        `${PIPELINE_BASE_URL}/steps/${stepId}`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || `Failed to get step ${stepId}`
      );
    }
  }

  /**
   * Create a new pipeline step
   */
  async createStep(step: PipelineStepRequest): Promise<PipelineStep> {
    try {
      const response = await axios.post<PipelineStep>(
        `${PIPELINE_BASE_URL}/steps`,
        step,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to create pipeline step'
      );
    }
  }

  /**
   * Update an existing pipeline step
   */
  async updateStep(stepId: number, step: PipelineStepRequest): Promise<PipelineStep> {
    try {
      const response = await axios.put<PipelineStep>(
        `${PIPELINE_BASE_URL}/steps/${stepId}`,
        step,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || `Failed to update step ${stepId}`
      );
    }
  }

  /**
   * Delete a pipeline step
   */
  async deleteStep(stepId: number): Promise<void> {
    try {
      await axios.delete(
        `${PIPELINE_BASE_URL}/steps/${stepId}`,
        { headers: this.getAuthHeaders() }
      );
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || `Failed to delete step ${stepId}`
      );
    }
  }

  /**
   * Reorder pipeline steps
   */
  async reorderSteps(stepIds: number[]): Promise<StepReorderResponse> {
    try {
      const response = await axios.post<StepReorderResponse>(
        `${PIPELINE_BASE_URL}/steps/reorder`,
        { step_ids: stepIds } as StepReorderRequest,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to reorder steps'
      );
    }
  }

  // ==================== AI MODELS ====================

  /**
   * Get all available AI models
   */
  async getAvailableModels(enabledOnly: boolean = false): Promise<AIModel[]> {
    try {
      const response = await axios.get<AIModel[]>(
        `${PIPELINE_BASE_URL}/models`,
        {
          headers: this.getAuthHeaders(),
          params: { enabled_only: enabledOnly }
        }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get available models'
      );
    }
  }

  /**
   * Get a single AI model by ID
   */
  async getModel(modelId: number): Promise<AIModel> {
    try {
      const response = await axios.get<AIModel>(
        `${PIPELINE_BASE_URL}/models/${modelId}`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || `Failed to get model ${modelId}`
      );
    }
  }
}

// Export singleton instance
export const pipelineApi = new PipelineApiService();

// Export class for testing
export default PipelineApiService;
