// Settings related types for the frontend

export enum DocumentClass {
  ARZTBRIEF = 'arztbrief',
  BEFUNDBERICHT = 'befundbericht',
  LABORWERTE = 'laborwerte'
}

export interface PipelineStepConfig {
  enabled: boolean;
  order: number;
  name: string;
  description: string;
}

export interface DocumentPrompts {
  document_type: DocumentClass;
  medical_validation_prompt: string;
  classification_prompt: string;
  preprocessing_prompt: string;
  translation_prompt: string;
  fact_check_prompt: string;
  grammar_check_prompt: string;
  language_translation_prompt: string;
  final_check_prompt: string;
  formatting_prompt: string;
  pipeline_steps: Record<string, PipelineStepConfig>;
  version?: number;
  last_modified?: string;
  modified_by?: string;
}

export interface PromptsMetadata {
  version: number;
  last_modified: string | null;
  modified_by: string | null;
}

export interface PromptsResponse {
  document_type: string;
  prompts: DocumentPrompts;
  metadata: PromptsMetadata;
}

export interface AuthRequest {
  code: string;
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  message: string;
}

export interface PromptUpdateRequest {
  prompts: DocumentPrompts;
  user?: string;
}

export interface PromptTestRequest {
  prompt: string;
  sample_text: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface PromptTestResponse {
  result: string;
  processing_time: number;
  model_used: string;
  tokens_used?: number;
}

export interface DocumentTypeInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
  examples: string[];
}

export interface ExportData {
  export_date: string;
  version: number;
  prompts: Record<string, any>;
}

export interface ImportRequest {
  data: ExportData;
}

export interface ImportResponse {
  success: boolean;
  message: string;
  results: Record<string, boolean>;
}

// Pipeline optimization request/response types
export interface PipelineSettingsUpdateRequest {
  settings: Partial<PipelineSettings>;
}

export interface PipelineSettingsResponse {
  settings: PipelineSettings;
  success: boolean;
  message: string;
  warning?: string;
}

// Document type descriptions for UI
export const DOCUMENT_TYPE_INFO: Record<DocumentClass, DocumentTypeInfo> = {
  [DocumentClass.ARZTBRIEF]: {
    id: 'arztbrief',
    name: 'Arztbrief',
    description: 'Briefe zwischen Ärzten, Entlassungsbriefe, Überweisungen',
    icon: '📨',
    examples: ['Entlassungsbrief', 'Überweisungsschreiben', 'Konsiliarbericht', 'Therapiebericht']
  },
  [DocumentClass.BEFUNDBERICHT]: {
    id: 'befundbericht',
    name: 'Befundbericht',
    description: 'Medizinische Befunde, Untersuchungsergebnisse, Bildgebung',
    icon: '🔬',
    examples: ['MRT-Befund', 'CT-Bericht', 'Ultraschallbefund', 'Pathologiebefund']
  },
  [DocumentClass.LABORWERTE]: {
    id: 'laborwerte',
    name: 'Laborwerte',
    description: 'Laborergebnisse, Blutwerte, Messwerte mit Referenzbereichen',
    icon: '🧪',
    examples: ['Blutbild', 'Urinanalyse', 'Hormonwerte', 'Tumormarker']
  }
};

// Pipeline optimization settings
export interface PipelineSettings {
  use_optimized_pipeline: boolean;
  pipeline_cache_timeout: number;
  enable_medical_validation: boolean;
  enable_classification: boolean;
  enable_preprocessing: boolean;
  enable_translation: boolean;
  enable_fact_check: boolean;
  enable_grammar_check: boolean;
  enable_language_translation: boolean;
  enable_final_check: boolean;
  enable_formatting: boolean;
}

export interface PipelineStatsResponse {
  pipeline_mode: string;
  cache_statistics: {
    total_entries: number;
    active_entries: number;
    expired_entries: number;
    cache_timeout_seconds: number;
  };
  performance_improvements: Record<string, string>;
}

// Prompt step descriptions for UI
export const PROMPT_STEPS = {
  medical_validation_prompt: {
    name: 'Medizinische Validierung',
    description: 'KI-gestützte Erkennung medizinischer Inhalte',
    placeholder: 'Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält...'
  },
  classification_prompt: {
    name: 'Klassifizierung',
    description: 'Prompt zur automatischen Dokumenttyp-Erkennung',
    placeholder: 'Analysiere diesen medizinischen Text und bestimme...'
  },
  preprocessing_prompt: {
    name: 'Vorverarbeitung',
    description: 'Entfernung persönlicher Daten und Bereinigung',
    placeholder: 'Entferne persönliche Daten aber behalte alle medizinischen Informationen...'
  },
  translation_prompt: {
    name: 'Hauptübersetzung',
    description: 'Übersetzung in patientenfreundliche Sprache',
    placeholder: 'Übersetze diesen medizinischen Text in einfache Sprache...'
  },
  fact_check_prompt: {
    name: 'Faktenprüfung',
    description: 'Überprüfung der medizinischen Korrektheit',
    placeholder: 'Prüfe diesen Text auf medizinische Korrektheit...'
  },
  grammar_check_prompt: {
    name: 'Grammatikprüfung',
    description: 'Korrektur von Grammatik und Rechtschreibung',
    placeholder: 'Korrigiere die deutsche Grammatik und Rechtschreibung...'
  },
  language_translation_prompt: {
    name: 'Sprachübersetzung',
    description: 'Übersetzung in andere Sprachen',
    placeholder: 'Übersetze diesen Text in {language}...'
  },
  final_check_prompt: {
    name: 'Finale Kontrolle',
    description: 'Abschließende Qualitätsprüfung',
    placeholder: 'Führe eine finale Qualitätskontrolle durch...'
  },
  formatting_prompt: {
    name: 'Textformatierung',
    description: 'Optimierung der Textstruktur und Lesbarkeit',
    placeholder: 'Formatiere diesen Text für optimale Lesbarkeit mit Überschriften und Listen...'
  }
};