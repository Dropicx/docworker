import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UploadZone from '../UploadZone';

describe('UploadZone Component', () => {
  it('renders upload zone with correct text', () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    expect(screen.getByText(/Dokument hochladen/i)).toBeInTheDocument();
    expect(screen.getByText(/PDF, JPG, JPEG oder PNG/i)).toBeInTheDocument();
  });

  it('shows file size limit', () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    expect(screen.getByText(/Maximale Dateigröße: 50MB/i)).toBeInTheDocument();
  });

  it('accepts valid file types', () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;
    expect(input.accept).toContain('.pdf');
    expect(input.accept).toContain('.jpg');
    expect(input.accept).toContain('.jpeg');
    expect(input.accept).toContain('.png');
  });

  it('calls onUpload when file is selected', async () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('file-input') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(mockOnUpload).toHaveBeenCalledWith(file);
    });
  });

  it('shows error for invalid file type', async () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    const file = new File(['test'], 'test.txt', { type: 'text/plain' });
    const input = screen.getByTestId('file-input') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText(/Ungültiger Dateityp/i)).toBeInTheDocument();
    });

    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it('shows error for oversized file', async () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    // Create file larger than 50MB
    const largeFile = new File(['x'.repeat(51 * 1024 * 1024)], 'large.pdf', {
      type: 'application/pdf',
    });
    const input = screen.getByTestId('file-input') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [largeFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Datei zu groß/i)).toBeInTheDocument();
    });

    expect(mockOnUpload).not.toHaveBeenCalled();
  });

  it('shows upload icon initially', () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    // Check for upload icon (look for svg element)
    const uploadIcon = screen.getByRole('img', { hidden: true });
    expect(uploadIcon).toBeInTheDocument();
  });

  it('handles drag and drop', async () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    const dropzone = screen.getByText(/Dokument hochladen/i).closest('div');
    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });

    if (dropzone) {
      fireEvent.drop(dropzone, {
        dataTransfer: {
          files: [file],
          types: ['Files'],
        },
      });

      await waitFor(() => {
        expect(mockOnUpload).toHaveBeenCalledWith(file);
      });
    }
  });

  it('shows drag over state when file is dragged over', () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    const dropzone = screen.getByText(/Dokument hochladen/i).closest('div');

    if (dropzone) {
      fireEvent.dragOver(dropzone);
      expect(dropzone).toHaveClass('border-brand-600'); // or whatever class indicates drag state
    }
  });

  it('clears error when new file is selected', async () => {
    const mockOnUpload = vi.fn();
    render(<UploadZone onUpload={mockOnUpload} />);

    const input = screen.getByTestId('file-input') as HTMLInputElement;

    // First, upload invalid file
    const invalidFile = new File(['test'], 'test.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Ungültiger Dateityp/i)).toBeInTheDocument();
    });

    // Then upload valid file
    const validFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.queryByText(/Ungültiger Dateityp/i)).not.toBeInTheDocument();
    });
  });
});
