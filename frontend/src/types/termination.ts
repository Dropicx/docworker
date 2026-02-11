/**
 * Pipeline Termination Types
 *
 * Types for handling early pipeline termination (e.g., content validation failed)
 */

export interface TerminationInfo {
  terminated: boolean;
  termination_step?: string;
  termination_reason?: string;
  termination_message?: string;
  matched_value?: string;
}

export const isTerminated = (result: unknown): result is TerminationInfo => {
  return (
    typeof result === 'object' && result !== null && (result as TerminationInfo).terminated === true
  );
};
