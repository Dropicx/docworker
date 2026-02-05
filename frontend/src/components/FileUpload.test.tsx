/**
 * FileUpload Component Tests
 *
 * Comprehensive test suite for the FileUpload component covering:
 * - Rendering and UI states
 * - File selection
 * - File validation
 * - Privacy checkbox flow
 * - Start processing flow
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, act } from '@testing-library/react';
import { renderWithRouter, userEvent } from '../test/helpers/renderWithProviders';
import { createMockFile } from '../test/helpers/testData';
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

const mockLanguages = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
];

describe('FileUpload Component', () => {
  const mockOnStartProcessing = vi.fn();
  const mockOnUploadError = vi.fn();

  const defaultProps = {
    onStartProcessing: mockOnStartProcessing,
    onUploadError: mockOnUploadError,
    availableLanguages: mockLanguages,
    languagesLoaded: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ApiService.validateFile).mockReturnValue({ valid: true });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  // ==================== Rendering Tests ====================

  describe('Rendering', () => {
    it('should render upload area', () => {
      renderWithRouter(<FileUpload {...defaultProps} />);

      expect(screen.getByText('upload.title')).toBeInTheDocument();
    });

    it('should render with disabled state', () => {
      renderWithRouter(<FileUpload {...defaultProps} disabled={true} />);

      const dropzone = screen.getByTestId('dropzone');
      expect(dropzone).toHaveClass('opacity-50');
    });
  });

  // ==================== File Selection Tests ====================

  describe('File Selection', () => {
    it('should display selected file', async () => {
      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });
    });

    it('should allow multiple file selection', async () => {
      renderWithRouter(<FileUpload {...defaultProps} />);

      const files = [createMockFile('document1.pdf'), createMockFile('document2.pdf')];

      simulateFileDrop(files);

      await waitFor(() => {
        expect(screen.getByText('upload.selectedFiles')).toBeInTheDocument();
      });
    });

    it('should clear all files', async () => {
      const user = userEvent.setup();

      renderWithRouter(<FileUpload {...defaultProps} />);

      const files = [createMockFile('document1.pdf')];
      simulateFileDrop(files);

      await waitFor(() => {
        expect(screen.getByText('upload.selectedFiles')).toBeInTheDocument();
      });

      const clearButton = screen.getByText('upload.removeAll');
      await user.click(clearButton);

      await waitFor(() => {
        expect(screen.queryByText('upload.selectedFiles')).not.toBeInTheDocument();
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

      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile('document.docx', 1024000, 'application/msword');
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('Dateityp nicht unterstützt')).toBeInTheDocument();
      });
    });

    it('should reject oversized files', async () => {
      vi.mocked(ApiService.validateFile).mockReturnValue({
        valid: false,
        error: 'Datei zu groß',
      });

      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile('huge.pdf', 60 * 1024 * 1024);
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText('Datei zu groß')).toBeInTheDocument();
      });
    });

    it('should accept valid PDF files', async () => {
      renderWithRouter(<FileUpload {...defaultProps} />);

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
      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        expect(screen.getByText(/upload\.privacyConsentPrefix/)).toBeInTheDocument();
      });
    });

    it('should disable submit button when privacy not accepted', async () => {
      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /upload.startProcessing/ });
        expect(submitButton).toBeDisabled();
      });
    });

    it('should enable submit button when privacy accepted', async () => {
      const user = userEvent.setup();

      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /upload.startProcessing/ });
      expect(submitButton).toBeEnabled();
    });
  });

  // ==================== Start Processing Tests ====================

  describe('Start Processing', () => {
    it('should call onStartProcessing when submit is clicked', async () => {
      const user = userEvent.setup();

      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /upload.startProcessing/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnStartProcessing).toHaveBeenCalledWith(file, null);
      });
    });

    it('should clear files after starting processing', async () => {
      const user = userEvent.setup();

      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const checkbox = screen.getByRole('checkbox');
        expect(checkbox).toBeInTheDocument();
      });

      const checkbox = screen.getByRole('checkbox');
      await user.click(checkbox);

      const submitButton = screen.getByRole('button', { name: /upload.startProcessing/ });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.queryByText('test-document.pdf')).not.toBeInTheDocument();
      });
    });

    it('should not call onStartProcessing without privacy acceptance', async () => {
      renderWithRouter(<FileUpload {...defaultProps} />);

      const file = createMockFile();
      simulateFileDrop([file]);

      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /upload.startProcessing/ });
        expect(submitButton).toBeDisabled();
      });

      expect(mockOnStartProcessing).not.toHaveBeenCalled();
    });
  });
});
