import axios, { AxiosError } from 'axios';
import {
  DocumentClass,
  DocumentPrompts,
  PromptsResponse,
  AuthRequest,
  AuthResponse,
  PromptUpdateRequest,
  PromptTestRequest,
  PromptTestResponse,
  DocumentTypeInfo,
  ExportData,
  ImportRequest,
  ImportResponse,
  PipelineSettings,
  PipelineSettingsUpdateRequest,
  PipelineSettingsResponse,
  PipelineStatsResponse,
  GlobalPrompts,
  GlobalPromptsResponse,
  GlobalPromptUpdateRequest
} from '../types/settings';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';
const SETTINGS_BASE_URL = `${API_BASE_URL}/settings`;

// Token management
const TOKEN_KEY = 'settings_auth_token';

class SettingsService {
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

  // Save token to localStorage
  private saveToken(token: string) {
    this.token = token;
    localStorage.setItem(TOKEN_KEY, token);
  }

  // Clear token
  public clearToken() {
    this.token = null;
    localStorage.removeItem(TOKEN_KEY);
  }

  // Check if authenticated
  public isAuthenticated(): boolean {
    return !!this.token;
  }

  /**
   * Authenticate with access code
   */
  async authenticate(code: string): Promise<AuthResponse> {
    try {
      const response = await axios.post<AuthResponse>(
        `${SETTINGS_BASE_URL}/auth`,
        { password: code } as AuthRequest
      );

      if (response.data.success && response.data.session_token) {
        this.saveToken(response.data.session_token);
      }

      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Authentication failed'
      );
    }
  }

  /**
   * Check if current session is authenticated
   */
  async checkAuth(): Promise<boolean> {
    // If no token, don't make the request
    if (!this.token) {
      return false;
    }
    
    try {
      const response = await axios.get(
        `${SETTINGS_BASE_URL}/check-auth`,
        { headers: this.getAuthHeaders() }
      );
      return response.data.authenticated;
    } catch {
      this.clearToken();
      return false;
    }
  }

  /**
   * Get prompts for a specific document type
   */
  async getPrompts(documentType: DocumentClass): Promise<PromptsResponse> {
    try {
      const response = await axios.get<PromptsResponse>(
        `${SETTINGS_BASE_URL}/document-prompts/${documentType}`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to load prompts'
      );
    }
  }

  /**
   * Update prompts for a specific document type
   */
  async updatePrompts(
    documentType: DocumentClass,
    prompts: DocumentPrompts,
    user?: string
  ): Promise<{ success: boolean; message: string; version: number }> {
    try {
      const response = await axios.put(
        `${SETTINGS_BASE_URL}/document-prompts/${documentType}`,
        { prompts, user } as PromptUpdateRequest,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to update prompts'
      );
    }
  }

  /**
   * Reset prompts to defaults for a specific document type
   */
  async resetPrompts(documentType: DocumentClass): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axios.post(
        `${SETTINGS_BASE_URL}/prompts/${documentType}/reset`,
        {},
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to reset prompts'
      );
    }
  }

  /**
   * Test a prompt with sample text
   */
  async testPrompt(request: PromptTestRequest): Promise<PromptTestResponse> {
    try {
      const response = await axios.post<PromptTestResponse>(
        `${SETTINGS_BASE_URL}/test-prompt`,
        request,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Prompt test failed'
      );
    }
  }

  /**
   * Get list of document types
   */
  async getDocumentTypes(): Promise<DocumentTypeInfo[]> {
    try {
      const response = await axios.get<{ document_types: DocumentTypeInfo[] }>(
        `${SETTINGS_BASE_URL}/document-types`,
        { headers: this.getAuthHeaders() }
      );
      return response.data.document_types;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to load document types'
      );
    }
  }

  /**
   * Export prompts
   */
  async exportPrompts(documentType?: DocumentClass): Promise<ExportData> {
    try {
      const url = documentType
        ? `${SETTINGS_BASE_URL}/export?document_type=${documentType}`
        : `${SETTINGS_BASE_URL}/export`;

      const response = await axios.get<ExportData>(
        url,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to export prompts'
      );
    }
  }

  /**
   * Import prompts
   */
  async importPrompts(data: ExportData): Promise<ImportResponse> {
    try {
      const response = await axios.post<ImportResponse>(
        `${SETTINGS_BASE_URL}/import`,
        { data } as ImportRequest,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to import prompts'
      );
    }
  }

  /**
   * Download export as file
   */
  downloadExport(exportData: ExportData, filename: string = 'prompts_export.json') {
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);

    const link = document.createElement('a');
    link.href = dataUri;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /**
   * Read import file
   */
  async readImportFile(file: File): Promise<ExportData> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target?.result as string);

          // Validate structure
          if (!data.prompts || typeof data.prompts !== 'object') {
            throw new Error('Invalid import file structure');
          }

          resolve(data as ExportData);
        } catch (error) {
          reject(new Error('Invalid JSON file'));
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read file'));
      };

      reader.readAsText(file);
    });
  }

  // Pipeline Step Management Methods

  async getPipelineSteps(documentType: DocumentClass): Promise<Record<string, any>> {
    try {
      const response = await axios.get(
        `${SETTINGS_BASE_URL}/pipeline-steps`,
        { headers: this.getAuthHeaders() }
      );
      return response.data.pipeline_steps;
    } catch (error) {
      console.error('Failed to get pipeline steps:', error);
      throw new Error('Failed to get pipeline steps');
    }
  }

  async updatePipelineStep(
    documentType: DocumentClass,
    stepName: string,
    enabled: boolean
  ): Promise<Record<string, any>> {
    try {
      const response = await axios.put(
        `${SETTINGS_BASE_URL}/pipeline-steps`,
        {
          step_name: stepName,
          enabled: enabled
        },
        { headers: this.getAuthHeaders() }
      );
      return response.data.pipeline_steps;
    } catch (error) {
      console.error('Failed to update pipeline step:', error);
      throw new Error('Failed to update pipeline step');
    }
  }

  async resetPipelineSteps(documentType: DocumentClass): Promise<Record<string, any>> {
    // Pipeline steps reset is not implemented in unified system
    // Return current pipeline steps instead
    return this.getPipelineSteps(documentType);
  }

  // Pipeline optimization settings methods

  /**
   * Get current pipeline settings
   */
  async getPipelineSettings(): Promise<PipelineSettings> {
    try {
      const response = await axios.get<{ settings: PipelineSettings }>(
        `${SETTINGS_BASE_URL}/pipeline-settings`,
        { headers: this.getAuthHeaders() }
      );
      return response.data.settings;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get pipeline settings'
      );
    }
  }

  /**
   * Update pipeline settings
   */
  async updatePipelineSettings(settings: Partial<PipelineSettings>): Promise<PipelineSettingsResponse> {
    try {
      const response = await axios.put<PipelineSettingsResponse>(
        `${SETTINGS_BASE_URL}/pipeline-settings`,
        { settings } as PipelineSettingsUpdateRequest,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to update pipeline settings'
      );
    }
  }

  /**
   * Get pipeline statistics
   */
  async getPipelineStats(): Promise<PipelineStatsResponse> {
    try {
      const response = await axios.get<PipelineStatsResponse>(
        `${API_BASE_URL}/process/pipeline-stats`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get pipeline statistics'
      );
    }
  }

  /**
   * Clear pipeline cache
   */
  async clearPipelineCache(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/process/clear-cache`,
        {},
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to clear pipeline cache'
      );
    }
  }

  // Global Prompts management methods

  /**
   * Get global/universal prompts
   */
  async getGlobalPrompts(): Promise<GlobalPromptsResponse> {
    try {
      const response = await axios.get<GlobalPromptsResponse>(
        `${SETTINGS_BASE_URL}/universal-prompts`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to get global prompts'
      );
    }
  }

  /**
   * Update global/universal prompts
   */
  async updateGlobalPrompts(prompts: GlobalPromptUpdateRequest): Promise<{ success: boolean; message: string; version: number }> {
    try {
      const response = await axios.put(
        `${SETTINGS_BASE_URL}/universal-prompts`,
        prompts,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to update global prompts'
      );
    }
  }

  /**
   * Reset global prompts to defaults
   */
  async resetGlobalPrompts(): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axios.post(
        `${SETTINGS_BASE_URL}/global-prompts/reset`,
        {},
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to reset global prompts'
      );
    }
  }

  /**
   * Export global prompts
   */
  async exportGlobalPrompts(): Promise<any> {
    try {
      const response = await axios.get(
        `${SETTINGS_BASE_URL}/global-prompts/export`,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to export global prompts'
      );
    }
  }

  /**
   * Import global prompts
   */
  async importGlobalPrompts(data: any): Promise<{ success: boolean; message: string }> {
    try {
      const response = await axios.post(
        `${SETTINGS_BASE_URL}/global-prompts/import`,
        { data },
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Failed to import global prompts'
      );
    }
  }

  /**
   * Test a global prompt
   */
  async testGlobalPrompt(request: PromptTestRequest): Promise<PromptTestResponse> {
    try {
      const response = await axios.post<PromptTestResponse>(
        `${SETTINGS_BASE_URL}/global-prompts/test`,
        request,
        { headers: this.getAuthHeaders() }
      );
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError<any>;
      throw new Error(
        axiosError.response?.data?.detail || 'Global prompt test failed'
      );
    }
  }
}

// Export singleton instance
const settingsService = new SettingsService();
export default settingsService;