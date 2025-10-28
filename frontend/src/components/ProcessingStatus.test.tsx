/**
 * ProcessingStatus Component Tests
 *
 * Comprehensive test suite covering:
 * - Rendering and loading states
 * - Polling mechanism (start, stop, intervals)
 * - Status updates and progress display
 * - Completion, error, and termination handling
 * - Cancellation functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, act } from '@testing-library/react';
import { renderWithRouter, userEvent } from '../test/helpers/renderWithProviders';
import { createMockProcessingProgress } from '../test/helpers/testData';
import ProcessingStatus from './ProcessingStatus';
import ApiService from '../services/api';

// Mock ApiService
vi.mock('../services/api', () => ({
  default: {
    getProcessingStatus: vi.fn(),
    cancelProcessing: vi.fn(),
    getStatusColor: vi.fn((status: string) => `status-${status}`),
    getStatusText: vi.fn((status: string) => status.toUpperCase()),
  },
}));

// Mock termination utilities
vi.mock('../utils/termination', () => ({
  isTerminated: vi.fn((progress) => progress.terminated === true),
  getTerminationMetadata: vi.fn((progress) => ({
    message: progress.termination_message || 'Terminated',
    reason: progress.termination_reason,
    step: progress.termination_step,
  })),
}));

describe('ProcessingStatus Component', () => {
  const mockOnComplete = vi.fn();
  const mockOnError = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  // ==================== Rendering Tests ====================

  describe('Rendering', () => {
    it('should show loading state initially', () => {
      vi.mocked(ApiService.getProcessingStatus).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      expect(screen.getByText('Status wird geladen')).toBeInTheDocument();
      expect(screen.getByText('Verbindung zum Verarbeitungsserver...')).toBeInTheDocument();
    });

    it('should display status information once loaded', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({
        status: 'processing',
        progress_percent: 50,
        current_step: 'TRANSLATION',
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(screen.getByText('KI-Verarbeitung')).toBeInTheDocument();
          expect(screen.getByText('50%')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should display progress bar', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({
        progress_percent: 75,
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(screen.getByText('75%')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  // ==================== Polling Mechanism Tests ====================

  describe('Polling Mechanism', () => {
    it('should poll status immediately on mount', async () => {
      const mockStatus = createMockProcessingProgress();
      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(ApiService.getProcessingStatus).toHaveBeenCalledWith('test-id');
      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(1);
    });

    it('should poll status every 2 seconds', async () => {
      const mockStatus = createMockProcessingProgress({ status: 'processing' });
      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      // Initial call
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(1);

      // After 2 seconds
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(2);

      // After 4 seconds total
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000);
      });

      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(3);
    });

    it('should stop polling when status is completed', async () => {
      const mockStatus = createMockProcessingProgress({ status: 'completed', progress_percent: 100 });
      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const initialCalls = vi.mocked(ApiService.getProcessingStatus).mock.calls.length;

      // Advance time - polling should have stopped
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // Should not have made additional calls
      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(initialCalls);
    });

    it('should stop polling on error', async () => {
      const mockStatus = createMockProcessingProgress({ status: 'error', error: 'Processing failed' });
      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const initialCalls = vi.mocked(ApiService.getProcessingStatus).mock.calls.length;

      // Advance time - polling should have stopped
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(initialCalls);
    });

    it('should cleanup interval on unmount', async () => {
      const mockStatus = createMockProcessingProgress({ status: 'processing' });
      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      const { unmount } = renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const callsBeforeUnmount = vi.mocked(ApiService.getProcessingStatus).mock.calls.length;

      unmount();

      // Advance time after unmount
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      // Should not have made additional calls after unmount
      expect(ApiService.getProcessingStatus).toHaveBeenCalledTimes(callsBeforeUnmount);
    });
  });

  // ==================== Status Updates Tests ====================

  describe('Status Updates', () => {
    it('should update progress percentage', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      let callCount = 0;
      vi.mocked(ApiService.getProcessingStatus).mockImplementation(async () => {
        callCount++;
        return createMockProcessingProgress({
          progress_percent: callCount === 1 ? 30 : 60
        });
      });

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(screen.getByText('30%')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Wait for next poll (2 seconds)
      await waitFor(
        () => {
          expect(screen.getByText('60%')).toBeInTheDocument();
        },
        { timeout: 5000 }
      );
    });

    it('should display current step', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({
        current_step: 'Extracting text from PDF',
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(screen.getByText('Extracting text from PDF')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });
  });

  // ==================== Completion Tests ====================

  describe('Completion Handling', () => {
    it('should call onComplete when status is completed', async () => {
      const mockStatus = createMockProcessingProgress({
        status: 'completed',
        progress_percent: 100,
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      // Wait for the 1.5s delay before onComplete is called
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1500);
      });

      expect(mockOnComplete).toHaveBeenCalled();
    });
  });

  // ==================== Error Handling Tests ====================

  describe('Error Handling', () => {
    it('should call onError when status is error', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({
        status: 'error',
        error: 'Processing failed',
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(mockOnError).toHaveBeenCalledWith('Processing failed');
        },
        { timeout: 3000 }
      );
    });

    it('should handle API polling errors', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      vi.mocked(ApiService.getProcessingStatus).mockRejectedValue(new Error('Network error'));

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(mockOnError).toHaveBeenCalledWith('Network error');
        },
        { timeout: 3000 }
      );
    });

    it('should handle termination', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({
        terminated: true,
        termination_message: 'Non-medical content detected',
        termination_reason: 'non_medical_content',
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
        />
      );

      await waitFor(
        () => {
          expect(mockOnError).toHaveBeenCalled();
          const call = vi.mocked(mockOnError).mock.calls[0];
          expect(call[0]).toBe('Non-medical content detected');
          expect(call[1]).toBeDefined(); // Metadata passed
        },
        { timeout: 3000 }
      );
    });
  });

  // ==================== Cancellation Tests ====================

  describe('Cancellation', () => {
    it('should show cancel button when processing', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({ status: 'processing' });
      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
          onCancel={mockOnCancel}
        />
      );

      await waitFor(
        () => {
          const cancelButton = screen.getByTitle('Verarbeitung abbrechen');
          expect(cancelButton).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should call cancelProcessing and onCancel when cancel button clicked', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const user = userEvent.setup({ delay: null });
      const mockStatus = createMockProcessingProgress({ status: 'processing' });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);
      vi.mocked(ApiService.cancelProcessing).mockResolvedValue({
        message: 'Cancelled',
        processing_id: 'test-id',
      });

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
          onCancel={mockOnCancel}
        />
      );

      const cancelButton = await screen.findByTitle(
        'Verarbeitung abbrechen',
        {},
        { timeout: 3000 }
      );

      await user.click(cancelButton);

      await waitFor(
        () => {
          expect(ApiService.cancelProcessing).toHaveBeenCalledWith('test-id');
          expect(mockOnCancel).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });

    it('should not show cancel button when completed', async () => {
      vi.useRealTimers(); // Use real timers for UI updates

      const mockStatus = createMockProcessingProgress({
        status: 'completed',
        progress_percent: 100,
      });

      vi.mocked(ApiService.getProcessingStatus).mockResolvedValue(mockStatus);

      renderWithRouter(
        <ProcessingStatus
          processingId="test-id"
          onComplete={mockOnComplete}
          onError={mockOnError}
          onCancel={mockOnCancel}
        />
      );

      await waitFor(
        () => {
          expect(screen.getByText('100%')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      expect(screen.queryByTitle('Verarbeitung abbrechen')).not.toBeInTheDocument();
    });
  });
});
