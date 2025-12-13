/**
 * TypeScript types for Privacy Filter API
 * Issue #35 Phase 6 - Frontend Dashboard
 */

export interface FilterCapabilities {
  has_ner: boolean;
  spacy_model: string;
  removal_method: string;
  custom_terms_loaded: boolean;
}

export interface DetectionStats {
  pii_types_supported: string[];
  pii_types_count: number;
  medical_terms_count: number;
  drug_database_count: number;
  abbreviations_count: number;
  eponyms_count: number;
  loinc_codes_count: number;
}

export interface PrivacyMetrics {
  timestamp: string;
  filter_capabilities: FilterCapabilities;
  detection_stats: DetectionStats;
  performance_target_ms: number;
}

export interface LiveTestResult {
  input_length: number;
  output_length: number;
  processing_time_ms: number;
  pii_types_detected: string[];
  entities_detected: number;
  quality_score: number;
  review_recommended: boolean;
  passes_performance_target: boolean;
}

export interface PIIType {
  type: string;
  description: string;
  marker: string;
}

export interface PIITypesResponse {
  pii_types: PIIType[];
  total_count: number;
  timestamp: string;
}

export interface PrivacyHealth {
  status: 'healthy' | 'unhealthy';
  filter_ready: boolean;
  ner_available?: boolean;
  medical_terms_loaded?: boolean;
  drug_database_loaded?: boolean;
  error?: string;
  timestamp: string;
}
