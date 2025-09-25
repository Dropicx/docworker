// Settings related types for the frontend

export enum DocumentClass {
  ARZTBRIEF = 'arztbrief',
  BEFUNDBERICHT = 'befundbericht',
  LABORWERTE = 'laborwerte'
}

export interface DocumentPrompts {
  document_type: DocumentClass;
  classification_prompt: string;
  preprocessing_prompt: string;
  translation_prompt: string;
  fact_check_prompt: string;
  grammar_check_prompt: string;
  language_translation_prompt: string;
  final_check_prompt: string;
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

// Prompt step descriptions for UI
export const PROMPT_STEPS = {
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
  }
};