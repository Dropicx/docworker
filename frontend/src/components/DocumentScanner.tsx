import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, RotateCcw, Check, AlertCircle, Loader2, AlertTriangle } from 'lucide-react';
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
    documentAligned,
    imageQuality,
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

  // Calculate countdown seconds remaining
  const countdownSeconds = documentAligned && autoProgress > 0
    ? Math.ceil((1 - autoProgress) * 3)
    : 0;

  const statusBadge = (() => {
    if (phase === 'scanning') {
      // Document aligned and counting down to capture
      if (documentAligned && autoProgress > 0) {
        return (
          <div className="flex flex-col items-center gap-2">
            <span className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-base font-bold bg-green-500 text-white shadow-lg animate-pulse">
              <span className="w-6 h-6 flex items-center justify-center bg-white/20 rounded-full text-sm">
                {countdownSeconds}
              </span>
              {t('scanner.holdSteady')}
            </span>
            {/* Progress bar */}
            <div className="w-48 h-2 bg-white/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-400 transition-all duration-100 ease-linear"
                style={{ width: `${autoProgress * 100}%` }}
              />
            </div>
          </div>
        );
      }
      // Document not detected or not aligned
      if (!documentAligned) {
        return (
          <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-white/30 text-white backdrop-blur-sm">
            {t('scanner.alignWithFrame')}
          </span>
        );
      }
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

        {/* Video + overlay — always mounted to preserve stream, hidden when captured/processing */}
        <video
          ref={videoRef as React.RefObject<HTMLVideoElement>}
          className={`absolute inset-0 w-full h-full bg-black ${phase === 'captured' || phase === 'processing' ? 'hidden' : ''}`}
          style={{ objectFit: 'cover' }}
          playsInline
          autoPlay
          muted
        />
        <canvas
          ref={overlayCanvasRef as React.RefObject<HTMLCanvasElement>}
          className={`absolute inset-0 w-full h-full pointer-events-none ${phase === 'captured' || phase === 'processing' ? 'hidden' : ''}`}
          style={{ objectFit: 'cover' }}
        />

        {/* Processing phase — show spinner while enhancing image */}
        {phase === 'processing' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-black text-white space-y-4">
            <Loader2 className="w-12 h-12 animate-spin text-brand-400" />
            <p className="text-base font-medium">{t('scanner.optimizing')}</p>
          </div>
        )}

        {/* Captured phase — preview with quality info */}
        {phase === 'captured' && capturedImageUrl && (
          <div className="absolute inset-0 flex flex-col bg-black">
            {/* Quality warning banner */}
            {imageQuality && imageQuality.isBlurry && (
              <div className="bg-amber-500/90 px-4 py-2 flex items-center justify-center gap-2 text-white text-sm font-medium">
                <AlertTriangle className="w-4 h-4" />
                {t('scanner.imageBlurry')}
              </div>
            )}
            {/* Image preview */}
            <div className="flex-1 flex items-center justify-center p-2">
              <img
                src={capturedImageUrl}
                alt={t('scanner.scannedDocument')}
                className="max-w-full max-h-full object-contain rounded-lg"
              />
            </div>
            {/* Quality badge */}
            {imageQuality && (
              <div className="absolute bottom-20 left-1/2 -translate-x-1/2">
                <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium backdrop-blur-sm ${
                  imageQuality.isAcceptable
                    ? 'bg-green-500/80 text-white'
                    : 'bg-amber-500/80 text-white'
                }`}>
                  {imageQuality.isAcceptable ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      {t('scanner.goodQuality')}
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {t('scanner.lowQuality')}
                    </>
                  )}
                </span>
              </div>
            )}
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
