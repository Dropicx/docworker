/**
 * LanguageSelector Component Tests
 *
 * Comprehensive test suite covering:
 * - Rendering states (loading, error, success, disabled)
 * - Language loading from API
 * - Dropdown interaction and backdrop
 * - Search functionality (by name and code)
 * - Language selection and deselection
 * - Clear selection option
 * - Popular vs other languages separation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter, userEvent } from '../test/helpers/renderWithProviders';
import { createMockLanguagesResponse } from '../test/helpers/testData';
import LanguageSelector from './LanguageSelector';
import ApiService from '../services/api';

// Mock ApiService
vi.mock('../services/api', () => ({
  default: {
    getAvailableLanguages: vi.fn(),
  },
}));

describe('LanguageSelector Component', () => {
  const mockOnLanguageSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ==================== Rendering States ====================

  describe('Rendering States', () => {
    it('should show loading state initially', () => {
      vi.mocked(ApiService.getAvailableLanguages).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      expect(screen.getByText('Sprachen werden geladen...')).toBeInTheDocument();
      expect(screen.getByText('Übersetzung (optional)')).toBeInTheDocument();
    });

    it('should show error state when loading fails', async () => {
      vi.mocked(ApiService.getAvailableLanguages).mockRejectedValue(new Error('Network error'));

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprachen konnten nicht geladen werden')).toBeInTheDocument();
      });

      expect(screen.getByText('Erneut versuchen')).toBeInTheDocument();
    });

    it('should show language selector when loaded successfully', async () => {
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      expect(screen.getByText(/Optional: Wählen Sie eine Sprache/)).toBeInTheDocument();
    });

    it('should show disabled state when disabled prop is true', async () => {
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector
          onLanguageSelect={mockOnLanguageSelect}
          selectedLanguage={null}
          disabled={true}
        />
      );

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /Sprache auswählen/ });
        expect(button).toBeDisabled();
      });
    });
  });

  // ==================== Language Loading ====================

  describe('Language Loading', () => {
    it('should load languages on mount', async () => {
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(ApiService.getAvailableLanguages).toHaveBeenCalledTimes(1);
      });
    });

    it('should retry loading languages when retry button clicked', async () => {
      const user = userEvent.setup();

      // First call fails
      vi.mocked(ApiService.getAvailableLanguages).mockRejectedValueOnce(new Error('Network error'));

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Erneut versuchen')).toBeInTheDocument();
      });

      // Second call succeeds
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      const retryButton = screen.getByText('Erneut versuchen');
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      expect(ApiService.getAvailableLanguages).toHaveBeenCalledTimes(2);
    });
  });

  // ==================== Dropdown Interaction ====================

  describe('Dropdown Interaction', () => {
    it('should open dropdown when button clicked', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      expect(screen.getByPlaceholderText('Sprache suchen...')).toBeInTheDocument();
      expect(screen.getByText('Beliebte Sprachen')).toBeInTheDocument();
    });

    it('should close dropdown when button clicked again', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });

      // Open
      await user.click(button);
      expect(screen.getByPlaceholderText('Sprache suchen...')).toBeInTheDocument();

      // Close
      await user.click(button);
      expect(screen.queryByPlaceholderText('Sprache suchen...')).not.toBeInTheDocument();
    });

    it('should close dropdown when backdrop clicked', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      expect(screen.getByPlaceholderText('Sprache suchen...')).toBeInTheDocument();

      // Click backdrop (find the div with fixed inset-0 class)
      const backdrop = document.querySelector('.fixed.inset-0');
      expect(backdrop).toBeTruthy();
      await user.click(backdrop!);

      expect(screen.queryByPlaceholderText('Sprache suchen...')).not.toBeInTheDocument();
    });

    it('should not open dropdown when disabled', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector
          onLanguageSelect={mockOnLanguageSelect}
          selectedLanguage={null}
          disabled={true}
        />
      );

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /Sprache auswählen/ });
        expect(button).toBeDisabled();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      expect(screen.queryByPlaceholderText('Sprache suchen...')).not.toBeInTheDocument();
    });
  });

  // ==================== Search Functionality ====================

  describe('Search Functionality', () => {
    it('should filter languages by name', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      const searchInput = screen.getByPlaceholderText('Sprache suchen...');
      await user.type(searchInput, 'English');

      expect(screen.getByText('English')).toBeInTheDocument();
      expect(screen.queryByText(/Français/)).not.toBeInTheDocument();
    });

    it('should filter languages by code', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      const searchInput = screen.getByPlaceholderText('Sprache suchen...');
      await user.type(searchInput, 'pl');

      // Only Polish should match "pl" code
      expect(screen.getByText(/Polski/)).toBeInTheDocument();
      expect(screen.queryByText('English')).not.toBeInTheDocument();
      expect(screen.queryByText(/Français/)).not.toBeInTheDocument();
    });

    it('should show no results message when search yields nothing', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      const searchInput = screen.getByPlaceholderText('Sprache suchen...');
      await user.type(searchInput, 'xyz123');

      expect(screen.getByText(/Keine Sprachen gefunden für "xyz123"/)).toBeInTheDocument();
    });
  });

  // ==================== Language Selection ====================

  describe('Language Selection', () => {
    it('should call onLanguageSelect when language clicked', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      // Click English language
      const englishButton = screen.getByText('English').closest('button');
      await user.click(englishButton!);

      expect(mockOnLanguageSelect).toHaveBeenCalledWith('en');
      expect(mockOnLanguageSelect).toHaveBeenCalledTimes(1);
    });

    it('should deselect language when clicking selected language again', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage="en" />
      );

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /English/ });
        expect(button).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /English/ });
      await user.click(button);

      // Click English again to deselect (find in the dropdown list, not the main button)
      const englishButtons = screen.getAllByText('English');
      const englishInList = englishButtons.find(el =>
        el.closest('button')?.className.includes('px-6')
      );
      await user.click(englishInList!.closest('button')!);

      expect(mockOnLanguageSelect).toHaveBeenCalledWith(null);
    });

    it('should show selected language in button', async () => {
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage="en" />
      );

      await waitFor(() => {
        const button = screen.getByRole('button', { name: /English/ });
        expect(button).toBeInTheDocument();
        expect(button).not.toHaveTextContent('Sprache auswählen');
      });
    });

    it('should show clear selection option when language is selected', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage="en" />
      );

      await waitFor(() => {
        expect(screen.getByText('English')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /English/ });
      await user.click(button);

      expect(screen.getByText('❌ Keine Übersetzung')).toBeInTheDocument();
    });

    it('should clear selection when clear button clicked', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage="en" />
      );

      await waitFor(() => {
        expect(screen.getByText('English')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /English/ });
      await user.click(button);

      const clearButton = screen.getByText('❌ Keine Übersetzung');
      await user.click(clearButton);

      expect(mockOnLanguageSelect).toHaveBeenCalledWith('');
    });

    it('should separate popular and other languages', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      expect(screen.getByText('Beliebte Sprachen')).toBeInTheDocument();
      expect(screen.getByText('Alle Sprachen')).toBeInTheDocument();
    });

    it('should close dropdown after language selection', async () => {
      const user = userEvent.setup();
      const mockResponse = createMockLanguagesResponse();
      vi.mocked(ApiService.getAvailableLanguages).mockResolvedValue(mockResponse);

      renderWithRouter(
        <LanguageSelector onLanguageSelect={mockOnLanguageSelect} selectedLanguage={null} />
      );

      await waitFor(() => {
        expect(screen.getByText('Sprache auswählen (optional)')).toBeInTheDocument();
      });

      const button = screen.getByRole('button', { name: /Sprache auswählen/ });
      await user.click(button);

      expect(screen.getByPlaceholderText('Sprache suchen...')).toBeInTheDocument();

      const englishButton = screen.getByText('English').closest('button');
      await user.click(englishButton!);

      expect(screen.queryByPlaceholderText('Sprache suchen...')).not.toBeInTheDocument();
    });
  });
});
