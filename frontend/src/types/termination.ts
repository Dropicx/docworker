/**
 * Pipeline Termination Types
 *
 * Types for handling early pipeline termination (e.g., non-medical content)
 */

export interface TerminationInfo {
  terminated: boolean;
  termination_step?: string;
  termination_reason?: string;
  termination_message?: string;
  matched_value?: string;
}

export const isTerminated = (result: any): result is TerminationInfo => {
  return result && result.terminated === true;
};
