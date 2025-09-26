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
  password: string;
}

export interface AuthResponse {
  success: boolean;
  session_token?: string;
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

// Global prompts interfaces
export interface GlobalPrompts {
  medical_validation_prompt: string;
  classification_prompt: string;
  preprocessing_prompt: string;
  language_translation_prompt: string;
}

export interface GlobalPromptsMetadata {
  version: number;
  last_modified: string | null;
  modified_by: string | null;
}

export interface GlobalPromptsResponse {
  global_prompts: GlobalPrompts;
  metadata: GlobalPromptsMetadata;
  statistics: Record<string, any>;
}

export interface GlobalPromptUpdateRequest {
  medical_validation_prompt: string;
  classification_prompt: string;
  preprocessing_prompt: string;
  language_translation_prompt: string;
  user?: string;
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

// Global prompt step descriptions for UI
export const GLOBAL_PROMPT_STEPS = {
  medical_validation_prompt: {
    name: '🔍 Medizinische Validierung (Universal)',
    description: 'Erkennt medizinische Inhalte - gilt für alle Dokumenttypen',
    placeholder: 'Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält...',
    category: 'preprocessing'
  },
  classification_prompt: {
    name: '📋 Dokumentklassifizierung (Universal)',
    description: 'Bestimmt den Dokumenttyp - gilt für alle Eingänge',
    placeholder: 'Analysiere diesen medizinischen Text und klassifiziere ihn als...',
    category: 'preprocessing'
  },
  preprocessing_prompt: {
    name: '🔒 Datenbereinigung (Universal)',
    description: 'Entfernt persönliche Daten - gilt für alle Dokumenttypen',
    placeholder: 'Entferne alle persönlichen Daten aus diesem Text...',
    category: 'preprocessing'
  },
  grammar_check_prompt: {
    name: '✏️ Grammatikprüfung (Universal)',
    description: 'Korrigiert Sprache - gilt für alle Dokumenttypen',
    placeholder: 'Korrigiere Grammatik und Rechtschreibung in diesem Text...',
    category: 'quality'
  },
  language_translation_prompt: {
    name: '🌍 Sprachübersetzung (Universal)',
    description: 'Template für Übersetzungen - gilt für alle Sprachen',
    placeholder: 'Übersetze diesen Text in {language}...',
    category: 'translation'
  }
};

// Document-specific prompt step descriptions for UI (universal prompts moved to GLOBAL_PROMPT_STEPS)
export const PROMPT_STEPS = {
  translation_prompt: {
    name: 'Hauptübersetzung',
    description: 'Übersetzung in patientenfreundliche Sprache (dokumentspezifisch)',
    placeholder: 'Übersetze diesen medizinischen Text in einfache Sprache...',
    category: 'translation'
  },
  fact_check_prompt: {
    name: 'Faktenprüfung',
    description: 'Überprüfung der medizinischen Korrektheit (dokumentspezifisch)',
    placeholder: 'Prüfe diesen Text auf medizinische Korrektheit...',
    category: 'quality'
  },
  final_check_prompt: {
    name: 'Finale Kontrolle',
    description: 'Abschließende Qualitätsprüfung (dokumentspezifisch)',
    placeholder: 'Führe eine finale Qualitätskontrolle durch...',
    category: 'quality'
  },
  formatting_prompt: {
    name: 'Textformatierung',
    description: 'Optimierung der Textstruktur und Lesbarkeit (dokumentspezifisch)',
    placeholder: 'Formatiere diesen Text für optimale Lesbarkeit mit Überschriften und Listen...',
    category: 'formatting'
  }
};

// Combined prompt categories
export const PROMPT_CATEGORIES = {
  preprocessing: {
    name: 'Vorverarbeitung',
    description: 'Universal für alle Dokumenttypen',
    color: 'blue'
  },
  quality: {
    name: 'Qualitätskontrolle',
    description: 'Universal für alle Dokumenttypen',
    color: 'green'
  },
  translation: {
    name: 'Übersetzung',
    description: 'Universal für alle Sprachen',
    color: 'purple'
  },
  document_specific: {
    name: 'Dokumentspezifisch',
    description: 'Angepasst für jeden Dokumenttyp',
    color: 'orange'
  }
};