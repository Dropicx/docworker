/**
 * TypeScript types for Modular Pipeline API
 */

// ==================== ENUMS ====================

export enum OCREngineEnum {
  TESSERACT = 'TESSERACT',
  PADDLEOCR = 'PADDLEOCR',
  VISION_LLM = 'VISION_LLM',
  HYBRID = 'HYBRID'
}

export enum ModelProvider {
  OVH = 'OVH',
  OPENAI = 'OPENAI',
  ANTHROPIC = 'ANTHROPIC',
  LOCAL = 'LOCAL'
}

// ==================== OCR CONFIGURATION ====================

export interface OCRConfig {
  lang?: string;
  psm?: number;
  oem?: number;
  use_gpu?: boolean;
  det_algorithm?: string;
  rec_algorithm?: string;
  model?: string;
  max_tokens?: number;
  temperature?: number;
  quality_threshold?: number;
  use_vision_for_complex?: boolean;
  fallback_engine?: string;
}

export interface OCRConfiguration {
  id: number;
  selected_engine: string;
  tesseract_config: OCRConfig | null;
  paddleocr_config: OCRConfig | null;
  vision_llm_config: OCRConfig | null;
  hybrid_config: OCRConfig | null;
  last_modified: string;
}

export interface OCRConfigRequest {
  selected_engine: OCREngineEnum;
  tesseract_config?: OCRConfig | null;
  paddleocr_config?: OCRConfig | null;
  vision_llm_config?: OCRConfig | null;
  hybrid_config?: OCRConfig | null;
}

// ==================== PIPELINE STEPS ====================

export interface PipelineStep {
  id: number;
  name: string;
  description: string | null;
  order: number;
  enabled: boolean;
  prompt_template: string;
  selected_model_id: number;
  temperature: number | null;
  max_tokens: number | null;
  retry_on_failure: boolean;
  max_retries: number;
  input_from_previous_step: boolean;
  output_format: string | null;
  created_at: string;
  last_modified: string;
  modified_by: string | null;

  // Pipeline branching fields
  document_class_id: number | null;
  is_branching_step: boolean;
  branching_field: string | null;
}

export interface PipelineStepRequest {
  name: string;
  description?: string | null;
  order: number;
  enabled: boolean;
  prompt_template: string;
  selected_model_id: number;
  temperature?: number | null;
  max_tokens?: number | null;
  retry_on_failure: boolean;
  max_retries: number;
  input_from_previous_step: boolean;
  output_format?: string | null;

  // Pipeline branching fields
  document_class_id?: number | null;
  is_branching_step?: boolean;
  branching_field?: string | null;
}

// ==================== AI MODELS ====================

export interface AIModel {
  id: number;
  name: string;
  display_name: string;
  provider: string;
  description: string | null;
  max_tokens: number | null;
  supports_vision: boolean;
  is_enabled: boolean;
}

// ==================== OCR ENGINE STATUS ====================

export interface EngineStatus {
  engine: string;
  available: boolean;
  description: string;
  speed: string;
  accuracy: string;
  cost: string;
  configuration: OCRConfig;
}

export interface EngineStatusMap {
  [key: string]: EngineStatus;
}

// ==================== REORDER REQUEST ====================

export interface StepReorderRequest {
  step_ids: number[];
}

// ==================== API RESPONSES ====================

export interface StepReorderResponse {
  success: boolean;
  message: string;
}

// ==================== DOCUMENT CLASSES ====================

export interface DocumentClass {
  id: number;
  class_key: string;
  display_name: string;
  description: string | null;
  icon: string | null;
  examples: string[] | null;
  strong_indicators: string[] | null;
  weak_indicators: string[] | null;
  is_enabled: boolean;
  is_system_class: boolean;
  created_at: string;
  last_modified: string;
  created_by: string | null;
}

export interface DocumentClassRequest {
  class_key: string;
  display_name: string;
  description?: string | null;
  icon?: string | null;
  examples?: string[] | null;
  strong_indicators?: string[] | null;
  weak_indicators?: string[] | null;
  is_enabled: boolean;
}

export interface DocumentClassStatistics {
  total_classes: number;
  enabled_classes: number;
  system_classes: number;
  custom_classes: number;
}

// ==================== PIPELINE VISUALIZATION ====================

export interface PipelineBranch {
  class_info: {
    id: number;
    class_key: string;
    display_name: string;
    description: string | null;
    icon: string | null;
    is_enabled: boolean;
    is_system_class: boolean;
  };
  steps: PipelineStep[];
}

export interface PipelineVisualization {
  universal_steps: PipelineStep[];
  branching_step: PipelineStep | null;
  branches: {
    [classKey: string]: PipelineBranch;
  };
}
