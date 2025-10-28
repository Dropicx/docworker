/**
 * FileUpload Component Tests
 *
 * Comprehensive test suite for the FileUpload component covering:
 * - Rendering and UI states
 * - File selection
 * - File validation
 * - Privacy checkbox flow
 * - Upload process
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, act } from '@testing-library/react';
import { renderWithRouter, userEvent } from '../test/helpers/renderWithProviders';
import { createMockFile, createMockUploadResponse } from '../test/helpers/testData';
import FileUpload from './FileUpload';
import ApiService from '../services/api';

// Mock the ApiService
vi.mock('../services/api', () => ({
  default: {
    uploadDocument: vi.fn(),
    validateFile: vi.fn(),
    formatFileSize: vi.fn((bytes: number) => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }),
  },
}));

// Create a mock onDrop function that we can control
let mockOnDrop: ((files: File[]) => void) | null = null;

// Mock react-dropzone
vi.mock('react-dropzone', () => ({
  useDropzone: vi.fn(({ onDrop }) => {
    mockOnDrop = onDrop;
    return {
      getRootProps: () => ({
        'data-testid': 'dropzone',
      }),
      getInputProps: () => ({
        'data-testid': 'file-input',
        type: 'file',
      }),
      isDragActive: false,
    };
  }),
}));

// Helper function to simulate file drop
const simulateFileDrop = (files: File[]) => {
  act(() => {
    if (mockOnDrop) {
      mockOnDrop(files);
    }
  });
};

describe('FileUpload Component', () => {
  const mockOnUploadSuccess = vi.fn();
  const mockOnUploadError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ApiService.validateFile).mockReturnValue({ valid: true });
    vi.mocked(ApiService.uploadDocument).mockResolvedValue(createMockUploadResponse());
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  // ==================== Rendering Tests ====================

  describe('Rendering', () => {
    it('should render upload area', () => {
      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      expect(screen.getByText('Dokumente hochladen')).toBeInTheDocument();
      expect(screen.getByText('Unterstützte Formate')).toBeInTheDocument();
    });

    it('should render with disabled state', () => {
      renderWithRouter(
        <FileUpload
          onUploadSuccess={mockOnUploadSuccess}
          onUploadError={mockOnUploadError}
          disabled={true}
        />
      );

      const dropzone = screen.getByTestId('dropzone');
      expect(dropzone).toHaveClass('opacity-50');
    });
  });

  // ==================== File Selection Tests ====================

  describe('File Selection', () => {
    it('should display selected file', async () => {
      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });
    });

    it('should allow multiple file selection', async () => {
      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const files = [createMockFile('document1.pdf'), createMockFile('document2.pdf')];

      simulateFileDrop(files);

      await waitFor(() => {
        expect(screen.getByText('Ausgewählte Dateien (2)')).toBeInTheDocument();
      });
    });

    it('should clear all files', async () => {
      const user = userEvent.setup();

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const files = [createMockFile('document1.pdf')];
      simulateFileDrop(files);

      await waitFor(() => {
        expect(screen.getByText('Ausgewählte Dateien (1)')).toBeInTheDocument();
      });

      const clearButton = screen.getByText('Alle entfernen');
      await user.click(clearButton);

      await waitFor(() => {
        expect(screen.queryByText('Ausgewählte Dateien')).not.toBeInTheDocument();
      });
    });
  });

  // ==================== File Validation Tests ====================

  describe('File Validation', () => {
    it('should reject unsupported file types', async () => {
      vi.mocked(ApiService.validateFile).mockReturnValue({
        valid: false,
        error: 'Dateityp nicht unterstützt',
      });

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile('document.docx', 1024000, 'application/msword');
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('Upload fehlgeschlagen')).toBeInTheDocument();
      });
    });

    it('should reject oversized files', async () => {
      vi.mocked(ApiService.validateFile).mockReturnValue({
        valid: false,
        error: 'Datei zu groß',
      });

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile('huge.pdf', 60 * 1024 * 1024);
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('Datei zu groß')).toBeInTheDocument();
      });
    });

    it('should accept valid PDF files', async () => {
      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile('valid.pdf');
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('valid.pdf')).toBeInTheDocument();
      });

      expect(mockOnUploadError).not.toHaveBeenCalled();
    });
  });

  // ==================== Privacy Checkbox Tests ====================

  describe('Privacy Checkbox', () => {
    it('should show privacy checkbox after file selection', async () => {
      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText(/Ich habe die/)).toBeInTheDocument();
      });
    });

    it('should disable submit button when privacy not accepted', async () => {
      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /Verarbeitung starten/ });
        expect(submitButton).toBeDisabled();
      });
    });

    it('should enable submit button when privacy accepted', async () => {
      const user = userEvent.setup();

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /Verarbeitung starten/ });
      expect(submitButton).toBeEnabled();
    });
  });

  // ==================== Upload Process Tests ====================

  describe('Upload Process', () => {
    it('should upload file successfully', async () => {
      const user = userEvent.setup();

      vi.mocked(ApiService.uploadDocument).mockResolvedValue(createMockUploadResponse());

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /Verarbeitung starten/ });
      await user.click(submitButton);

      // Wait for upload to complete
      await waitFor(
        () => {
          expect(ApiService.uploadDocument).toHaveBeenCalledWith(file);
          expect(mockOnUploadSuccess).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });

    it('should show upload progress overlay', async () => {
      const user = userEvent.setup();

      // Delay the upload response slightly to see the loading state
      vi.mocked(ApiService.uploadDocument).mockImplementation(
        () =>
          new Promise(resolve => {
            setTimeout(() => resolve(createMockUploadResponse()), 100);
          })
      );

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /Verarbeitung starten/ });
      await user.click(submitButton);

      // Check that upload overlay appears
      await waitFor(
        () => {
          expect(screen.getByText('Datei wird hochgeladen')).toBeInTheDocument();
        },
        { timeout: 1000 }
      );

      // Wait for upload to complete
      await waitFor(
        () => {
          expect(mockOnUploadSuccess).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });

    it('should handle upload error', async () => {
      const user = userEvent.setup();

      vi.mocked(ApiService.uploadDocument).mockRejectedValue(new Error('Network error'));

      renderWithRouter(
        <FileUpload onUploadSuccess={mockOnUploadSuccess} onUploadError={mockOnUploadError} />
      );

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /Verarbeitung starten/ });
      await user.click(submitButton);

      // Wait for error to appear
      await waitFor(
        () => {
          expect(screen.getByText('Upload fehlgeschlagen')).toBeInTheDocument();
          expect(mockOnUploadError).toHaveBeenCalledWith('Network error');
        },
        { timeout: 3000 }
      );
    });
  });
});
