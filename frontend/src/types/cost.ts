/**
 * Cost Statistics Types
 * TypeScript interfaces for the cost statistics dashboard (Issue #51)
 */

/**
 * Cost overview statistics
 */
export interface CostOverview {
  total_cost_usd: number;
  total_tokens: number;
  total_calls: number;
  average_cost_per_call: number;
  average_tokens_per_call: number;
}

/**
 * Cost breakdown for a single AI model
 */
export interface ModelCostBreakdown {
  calls: number;
  tokens: number;
  cost_usd: number;
  provider: string | null;
}

/**
 * Cost breakdown for a single pipeline step
 */
export interface StepCostBreakdown {
  calls: number;
  tokens: number;
  cost_usd: number;
}

/**
 * Cost breakdown by model and pipeline step
 */
export interface CostBreakdown {
  by_model: Record<string, ModelCostBreakdown>;
  by_step: Record<string, StepCostBreakdown>;
}

/**
 * Cost summary for a single processing job
 */
export interface ProcessingJobCost {
  processing_id: string;
  total_cost_usd: number;
  total_tokens: number;
  call_count: number;
  document_type: string | null;
  models_used: string[];
  created_at: string;
}

/**
 * Paginated list of processing jobs with costs
 */
export interface ProcessingJobsResponse {
  jobs: ProcessingJobCost[];
  total: number;
}

/**
 * Individual cost log entry for a processing job
 */
export interface CostLogEntry {
  id: number;
  step_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  model_name: string | null;
  processing_time_seconds: number | null;
  created_at: string;
}

/**
 * Detailed cost information for a specific processing job
 */
export interface ProcessingJobDetail {
  processing_id: string;
  entries: CostLogEntry[];
  summary: CostOverview;
}

/**
 * Date range filter presets
 */
export type DateRangePreset = 'today' | 'week' | 'month' | 'all';

/**
 * Sort options for processing jobs
 */
export type SortBy = 'cost' | 'date' | 'tokens';
export type SortOrder = 'asc' | 'desc';

/**
 * Query parameters for processing jobs endpoint
 */
export interface ProcessingJobsQuery {
  skip?: number;
  limit?: number;
  sort_by?: SortBy;
  sort_order?: SortOrder;
  search?: string;
}
