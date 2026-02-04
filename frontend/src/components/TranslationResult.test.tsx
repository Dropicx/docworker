/**
 * TranslationResult Component Tests
 *
 * Comprehensive test suite covering:
 * - Rendering and display states
 * - Tab switching (simplified vs language)
 * - Copy functionality with feedback
 * - Original text toggle
 * - PDF export functionality
 * - Callback handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders, userEvent } from '../test/helpers/renderWithProviders';
import { createMockTranslationResult } from '../test/helpers/testData';
import TranslationResult from './TranslationResult';
import ApiService from '../services/api';
import * as pdfExport from '../utils/pdfExportAdvanced';

// Mock useAuth to return admin user (original text section is admin-only)
vi.mock('../contexts/AuthContext', async () => {
  const actual = await vi.importActual('../contexts/AuthContext');
  return {
    ...(actual as object),
    useAuth: vi.fn(() => ({
      user: {
        id: '1',
        role: 'admin',
        email: 'admin@test.com',
        full_name: 'Admin User',
        is_active: true,
      },
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshTokens: vi.fn(),
    })),
  };
});

// Mock ApiService
vi.mock('../services/api', () => ({
  default: {
    formatDuration: vi.fn((seconds: number): string => {
      if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
      } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
      } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
      }
    }),
    getGuidelines: vi.fn().mockResolvedValue({
      processing_id: 'test-123',
      status: 'not_configured',
      timestamp: new Date().toISOString(),
    }),
  },
}));

// Mock PDF export utility
vi.mock('../utils/pdfExportAdvanced', () => ({
  exportToPDF: vi.fn().mockResolvedValue(undefined),
}));

// Mock ReactMarkdown to avoid complex rendering in tests
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));

// Mock remark-gfm
vi.mock('remark-gfm', () => ({
  default: vi.fn(),
}));

// Mock GuidelinesSection component
vi.mock('./GuidelinesSection', () => ({
  default: () => <div data-testid="guidelines-section">Guidelines Mock</div>,
}));

describe('TranslationResult Component', () => {
  const mockOnNewTranslation = vi.fn();
  let writeTextSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Mock clipboard.writeText as a proper spy
    writeTextSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    writeTextSpy.mockRestore();
  });

  // ==================== Rendering Tests ====================

  describe('Rendering', () => {
    it('should render translation result with all main sections', () => {
      const mockResult = createMockTranslationResult();

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Hero section
      expect(screen.getByText('Übersetzung abgeschlossen')).toBeInTheDocument();

      // Translation content - check for a substring since ReactMarkdown is mocked
      expect(screen.getByText(/Patient has diabetes/)).toBeInTheDocument();

      // Original text section
      expect(screen.getByText('Originaltext')).toBeInTheDocument();

      // New translation button
      expect(screen.getByText('Neues Dokument übersetzen')).toBeInTheDocument();

      // Disclaimer
      expect(screen.getByText('Wichtiger Hinweis')).toBeInTheDocument();
    });

    it('should display processing time', () => {
      const mockResult = createMockTranslationResult({
        processing_time_seconds: 12.5,
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      expect(ApiService.formatDuration).toHaveBeenCalledWith(12.5);
      expect(screen.getByText('Verarbeitet in')).toBeInTheDocument();
    });

    it('should show language card when language translation exists', () => {
      const mockResult = createMockTranslationResult({
        language_translated_text: 'English translation',
        target_language: 'en',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      expect(screen.getByText('Zielsprache')).toBeInTheDocument();
      // Multiple "EN" elements exist (language card + tab button), just check one exists
      expect(screen.getAllByText('EN').length).toBeGreaterThan(0);
    });

    it('should not show language card without language translation', () => {
      const mockResult = createMockTranslationResult({
        language_translated_text: null,
        target_language: null,
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      expect(screen.queryByText('Zielsprache')).not.toBeInTheDocument();
    });

    it('should show tabs when language translation exists', () => {
      const mockResult = createMockTranslationResult({
        language_translated_text: 'English translation',
        target_language: 'en',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      expect(screen.getByText('📄 Vereinfacht (Deutsch)')).toBeInTheDocument();
      // Multiple "EN" elements exist, just check at least one is present
      expect(screen.getAllByText('EN').length).toBeGreaterThan(0);
    });
  });

  // ==================== Tab Switching Tests ====================

  describe('Tab Switching', () => {
    it('should start with language tab active when language translation exists', () => {
      const mockResult = createMockTranslationResult({
        translated_text: 'German simplified text',
        language_translated_text: 'English translation',
        target_language: 'en',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Language tab should be active and showing language text
      expect(screen.getByText('English translation')).toBeInTheDocument();
    });

    it('should switch between simplified and language tabs', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        translated_text: 'German simplified text',
        language_translated_text: 'English translation',
        target_language: 'en',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Initially shows language text
      expect(screen.getByText('English translation')).toBeInTheDocument();

      // Click simplified tab
      const simplifiedTab = screen.getByText('📄 Vereinfacht (Deutsch)');
      await user.click(simplifiedTab);

      // Should now show simplified text
      expect(screen.getByText('German simplified text')).toBeInTheDocument();
    });

    it('should start with simplified tab when no language translation', () => {
      const mockResult = createMockTranslationResult({
        translated_text: 'German simplified text',
        language_translated_text: null,
        target_language: null,
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      expect(screen.getByText('German simplified text')).toBeInTheDocument();
    });
  });

  // ==================== Copy Functionality Tests ====================

  describe('Copy Functionality', () => {
    it('should copy translated text when copy button clicked', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        translated_text: 'Text to copy',
        language_translated_text: null, // No language translation
        target_language: null,
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      const copyButton = screen
        .getAllByRole('button')
        .find(btn => btn.textContent?.includes('Kopieren') || btn.textContent?.includes('Copy'));
      expect(copyButton).toBeDefined();

      await user.click(copyButton!);

      expect(writeTextSpy).toHaveBeenCalledWith('Text to copy');
    });

    it('should show "Kopiert!" feedback after copy', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        language_translated_text: null,
        target_language: null,
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      const copyButton = screen
        .getAllByRole('button')
        .find(btn => btn.textContent?.includes('Kopieren') || btn.textContent?.includes('Copy'));

      await user.click(copyButton!);

      // Should show "Kopiert!" feedback
      expect(screen.getByText('Kopiert!')).toBeInTheDocument();
    });

    it('should reset copy feedback after 2 seconds', async () => {
      vi.useRealTimers(); // Use real timers for setTimeout

      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        language_translated_text: null,
        target_language: null,
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      const copyButton = screen
        .getAllByRole('button')
        .find(btn => btn.textContent?.includes('Kopieren') || btn.textContent?.includes('Copy'));

      await user.click(copyButton!);

      await waitFor(() => {
        expect(screen.getByText('Kopiert!')).toBeInTheDocument();
      });

      // Wait for setTimeout to complete (2 seconds)
      await waitFor(
        () => {
          expect(screen.queryByText('Kopiert!')).not.toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should copy original text when visible', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        original_text: 'Original text to copy',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Show original text
      const showButton = screen.getByText('Anzeigen');
      await user.click(showButton);

      // Find and click copy button for original text
      const copyButtons = screen
        .getAllByRole('button')
        .filter(btn => btn.textContent?.includes('Kopieren') || btn.textContent?.includes('Copy'));
      // Second copy button is for original text
      await user.click(copyButtons[1]);

      expect(writeTextSpy).toHaveBeenCalledWith('Original text to copy');
    });
  });

  // ==================== Original Text Toggle Tests ====================

  describe('Original Text Toggle', () => {
    it('should not show original text initially', () => {
      const mockResult = createMockTranslationResult({
        original_text: 'Hidden original text',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      expect(screen.getByText('Anzeigen')).toBeInTheDocument();
      expect(screen.queryByText('Hidden original text')).not.toBeInTheDocument();
    });

    it('should show original text when Anzeigen clicked', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        original_text: 'Now visible original text',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      const showButton = screen.getByText('Anzeigen');
      await user.click(showButton);

      expect(screen.getByText('Now visible original text')).toBeInTheDocument();
      expect(screen.getByText('Ausblenden')).toBeInTheDocument();
    });

    it('should hide original text when Ausblenden clicked', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        original_text: 'Toggleable text',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Show
      const showButton = screen.getByText('Anzeigen');
      await user.click(showButton);

      expect(screen.getByText('Toggleable text')).toBeInTheDocument();

      // Hide
      const hideButton = screen.getByText('Ausblenden');
      await user.click(hideButton);

      expect(screen.queryByText('Toggleable text')).not.toBeInTheDocument();
    });

    it('should only show original copy button when text is visible', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult();

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Initially, only main copy button (for translation)
      const initialCopyButtons = screen
        .getAllByRole('button')
        .filter(btn => btn.textContent?.includes('Kopieren') || btn.textContent?.includes('Copy'));
      expect(initialCopyButtons.length).toBe(1);

      // Show original text
      const showButton = screen.getByText('Anzeigen');
      await user.click(showButton);

      // Now should have two copy buttons
      const copyButtonsAfter = screen
        .getAllByRole('button')
        .filter(btn => btn.textContent?.includes('Kopieren') || btn.textContent?.includes('Copy'));
      expect(copyButtonsAfter.length).toBe(2);
    });
  });

  // ==================== PDF Export Tests ====================

  describe('PDF Export', () => {
    it('should call exportToPDF when download button clicked', async () => {
      vi.useRealTimers(); // Use real timers for setTimeout

      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        translated_text: 'Export this text',
        language_translated_text: null,
        target_language: null,
        processing_time_seconds: 10.5,
        document_type_detected: 'ARZTBRIEF',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      const downloadButton = screen.getByText('Als PDF');
      await user.click(downloadButton);

      // Wait for setTimeout to complete (200ms)
      await waitFor(
        () => {
          expect(pdfExport.exportToPDF).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });

    it('should export with language suffix when language tab active', async () => {
      vi.useRealTimers(); // Use real timers for setTimeout

      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult({
        translated_text: 'German text',
        language_translated_text: 'English text',
        target_language: 'en',
        processing_time_seconds: 10.5,
        document_type_detected: 'ARZTBRIEF',
      });

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      // Language tab should be active by default
      const downloadButton = screen.getByText('Als PDF');
      await user.click(downloadButton);

      // Wait for setTimeout to complete (200ms)
      await waitFor(
        () => {
          expect(pdfExport.exportToPDF).toHaveBeenCalledWith(
            'pdf-export-content-temp',
            expect.stringContaining('_en.pdf'),
            expect.objectContaining({
              title: 'Übersetzung (EN)',
              content: 'English text',
              language: 'en',
              processingTime: 10.5,
              documentType: 'ARZTBRIEF',
            })
          );
        },
        { timeout: 3000 }
      );
    });
  });

  // ==================== Callback Tests ====================

  describe('Callbacks', () => {
    it('should call onNewTranslation when button clicked', async () => {
      const user = userEvent.setup({ delay: null });
      const mockResult = createMockTranslationResult();

      renderWithProviders(
        <TranslationResult result={mockResult} onNewTranslation={mockOnNewTranslation} />
      );

      const newTranslationButton = screen.getByText('Neues Dokument übersetzen');
      await user.click(newTranslationButton);

      expect(mockOnNewTranslation).toHaveBeenCalledTimes(1);
    });
  });
});
