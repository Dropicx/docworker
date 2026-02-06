import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, RotateCcw, Check, AlertCircle, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useDocumentScanner } from '../hooks/useDocumentScanner';
import CaptureButton from './scanner/CaptureButton';

interface DocumentScannerProps {
  isOpen: boolean;
  onCapture: (file: File) => void;
  onClose: () => void;
}

const DocumentScanner: React.FC<DocumentScannerProps> = ({ isOpen, onCapture, onClose }) => {
  const { t } = useTranslation();
  const {
    phase,
    videoRef,
    overlayCanvasRef,
    capturedImageUrl,
    autoProgress,
    errorMessage,
    startCamera,
    captureManual,
    confirmCapture,
    retake,
    cleanup,
  } = useDocumentScanner();

  useEffect(() => {
    if (isOpen) {
      startCamera();
    }
    return () => cleanup();
  }, [isOpen, startCamera, cleanup]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  const handleClose = useCallback(() => {
    cleanup();
    onClose();
  }, [cleanup, onClose]);

  const handleConfirm = useCallback(() => {
    const file = confirmCapture();
    if (file) {
      cleanup();
      onCapture(file);
    }
  }, [confirmCapture, cleanup, onCapture]);

  if (!isOpen) return null;

  const statusBadge = (() => {
    if (phase === 'scanning') {
      // Show progress indicator when auto-capture is counting down
      if (autoProgress > 0) {
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-500/90 text-white backdrop-blur-sm">
            {t('scanner.holdSteady')}
          </span>
        );
      }
      // Default: prompt user to align document
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-white/20 text-white backdrop-blur-sm">
          {t('scanner.alignWithFrame')}
        </span>
      );
    }
    return null;
  })();

  const content = (
    <div
      className="fixed inset-0 z-[100] bg-black flex flex-col"
      style={{
        paddingTop: 'env(safe-area-inset-top, 0px)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {/* Top bar */}
      <div className="relative z-10 flex items-center justify-between px-4 py-3">
        <button
          onClick={handleClose}
          className="w-10 h-10 flex items-center justify-center rounded-full bg-black/40 backdrop-blur-sm text-white"
          aria-label={t('scanner.close')}
        >
          <X className="w-5 h-5" />
        </button>
        {statusBadge}
        {/* Spacer to balance layout */}
        <div className="w-10" />
      </div>

      {/* Main content area */}
      <div className="flex-1 relative overflow-hidden">
        {/* Initializing phase */}
        {phase === 'initializing' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-white space-y-4">
            <Loader2 className="w-10 h-10 animate-spin text-white/80" />
            <p className="text-sm text-white/70">{t('scanner.starting')}</p>
          </div>
        )}

        {/* Error phase */}
        {phase === 'error' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-white space-y-4 px-8">
            <div className="w-16 h-16 rounded-full bg-red-500/20 flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-red-400" />
            </div>
            <p className="text-sm text-white/80 text-center leading-relaxed">
              {errorMessage || t('scanner.error')}
            </p>
            <button
              onClick={handleClose}
              className="px-6 py-2.5 bg-white/20 backdrop-blur-sm rounded-lg text-white text-sm font-medium"
            >
              {t('scanner.close')}
            </button>
          </div>
        )}

        {/* Video + overlay — always mounted to preserve stream, hidden when captured */}
        <video
          ref={videoRef as React.RefObject<HTMLVideoElement>}
          className={`absolute inset-0 w-full h-full object-cover ${phase === 'captured' ? 'hidden' : ''}`}
          playsInline
          autoPlay
          muted
        />
        <canvas
          ref={overlayCanvasRef as React.RefObject<HTMLCanvasElement>}
          className={`absolute inset-0 w-full h-full object-cover pointer-events-none ${phase === 'captured' ? 'hidden' : ''}`}
        />

        {/* Captured phase — preview */}
        {phase === 'captured' && capturedImageUrl && (
          <div className="absolute inset-0 flex items-center justify-center bg-black">
            <img
              src={capturedImageUrl}
              alt={t('scanner.scannedDocument')}
              className="max-w-full max-h-full object-contain"
            />
          </div>
        )}
      </div>

      {/* Bottom bar */}
      <div className="relative z-10 px-4 py-4">
        {/* Scanning controls */}
        {phase === 'scanning' && (
          <div className="flex items-center justify-center">
            <CaptureButton
              onCapture={captureManual}
              autoProgress={autoProgress}
            />
          </div>
        )}

        {/* Captured controls */}
        {phase === 'captured' && (
          <div className="flex items-center justify-center space-x-6">
            <button
              onClick={retake}
              className="flex flex-col items-center space-y-1 text-white"
            >
              <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <RotateCcw className="w-5 h-5" />
              </div>
              <span className="text-xs">{t('scanner.retake')}</span>
            </button>
            <button
              onClick={handleConfirm}
              className="flex flex-col items-center space-y-1 text-white"
            >
              <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center">
                <Check className="w-5 h-5" />
              </div>
              <span className="text-xs">{t('scanner.use')}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(content, document.body);
};

export default DocumentScanner;
