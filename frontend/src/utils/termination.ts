/**
 * Termination Detection Utilities
 *
 * Centralized termination handling for pipeline execution.
 * Provides type-safe detection and metadata extraction.
 */

import { ProcessingProgress } from '../types/api';

/**
 * Termination metadata structure
 */
export interface TerminationMetadata {
  isTermination: boolean;
  reason?: string;
  step?: string;
  message: string;
}

/**
 * Check if a processing response indicates termination
 *
 * @param status - Processing progress response from API
 * @returns true if pipeline was terminated, false otherwise
 *
 * @example
 * ```typescript
 * if (isTerminated(statusResponse)) {
 *   const metadata = getTerminationMetadata(statusResponse);
 *   showTerminationUI(metadata);
 * }
 * ```
 */
export function isTerminated(status: ProcessingProgress): boolean {
  return status.terminated === true;
}

/**
 * Extract termination metadata from processing response
 *
 * @param status - Processing progress response from API
 * @returns Structured termination metadata
 *
 * @example
 * ```typescript
 * const metadata = getTerminationMetadata(statusResponse);
 * console.log(`Terminated at: ${metadata.step}`);
 * console.log(`Reason: ${metadata.reason}`);
 * ```
 */
export function getTerminationMetadata(status: ProcessingProgress): TerminationMetadata {
  // Multi-level fallback for termination message
  const message =
    status.termination_message ||
    status.error ||
    status.message ||
    'Die Verarbeitung wurde gestoppt.';

  return {
    isTermination: true,
    reason: status.termination_reason,
    step: status.termination_step || status.current_step,
    message,
  };
}

/**
 * Get user-friendly termination title
 *
 * @param metadata - Termination metadata
 * @returns Localized title string
 */
export function getTerminationTitle(metadata: TerminationMetadata): string {
  if (
    metadata.reason === 'Non-medical content detected' ||
    metadata.reason === 'Content validation failed'
  ) {
    return 'Inhalt konnte nicht verarbeitet werden';
  }

  return 'Verarbeitung gestoppt';
}

/**
 * Check if termination is due to content validation (unsupported or non-processable content)
 *
 * @param metadata - Termination metadata
 * @returns true if content validation failed or non-medical content was detected
 */
export function isNonMedicalTermination(metadata: TerminationMetadata): boolean {
  return (
    metadata.reason === 'Non-medical content detected' ||
    metadata.reason === 'Content validation failed'
  );
}
