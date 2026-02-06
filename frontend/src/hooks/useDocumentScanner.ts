import { useState, useRef, useCallback, useEffect } from 'react';
import Scanner, { QualityWarning, QualityResult } from '../lib/jscanify';
import { useOpenCV } from './useOpenCV';

export type ScannerPhase = 'initializing' | 'scanning' | 'captured' | 'error';

interface CornerPoints {
  topLeftCorner: { x: number; y: number };
  topRightCorner: { x: number; y: number };
  bottomLeftCorner: { x: number; y: number };
  bottomRightCorner: { x: number; y: number };
}

interface UseDocumentScannerReturn {
  phase: ScannerPhase;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  overlayCanvasRef: React.RefObject<HTMLCanvasElement | null>;
  capturedImageUrl: string | null;
  autoProgress: number;
  opencvReady: boolean;
  errorMessage: string | null;
  qualityWarnings: QualityWarning[];
  startCamera: () => Promise<void>;
  captureManual: () => void;
  confirmCapture: () => File | null;
  retake: () => void;
  cleanup: () => void;
}

const DETECTION_FPS = 30;
const FRAME_INTERVAL = 1000 / DETECTION_FPS;
const AUTO_CAPTURE_DELAY_MS = 1000;
const PROCESSING_WIDTH = 640;
const STABILITY_THRESHOLD = 20; // px tolerance for corner movement
const KALMAN_SMOOTHING = 0.3; // Smoothing factor for corner positions (0 = no smoothing, 1 = instant)

function cornersStable(prev: CornerPoints | null, curr: CornerPoints | null): boolean {
  if (!prev || !curr) return false;
  const keys = ['topLeftCorner', 'topRightCorner', 'bottomLeftCorner', 'bottomRightCorner'] as const;
  for (const key of keys) {
    const dx = Math.abs(prev[key].x - curr[key].x);
    const dy = Math.abs(prev[key].y - curr[key].y);
    if (dx > STABILITY_THRESHOLD || dy > STABILITY_THRESHOLD) return false;
  }
  return true;
}

function smoothCorners(
  current: CornerPoints,
  previous: CornerPoints | null,
  factor: number
): CornerPoints {
  if (!previous) return current;

  const keys = ['topLeftCorner', 'topRightCorner', 'bottomLeftCorner', 'bottomRightCorner'] as const;
  const smoothed: CornerPoints = {
    topLeftCorner: { x: 0, y: 0 },
    topRightCorner: { x: 0, y: 0 },
    bottomLeftCorner: { x: 0, y: 0 },
    bottomRightCorner: { x: 0, y: 0 },
  };

  for (const key of keys) {
    smoothed[key] = {
      x: previous[key].x + factor * (current[key].x - previous[key].x),
      y: previous[key].y + factor * (current[key].y - previous[key].y),
    };
  }

  return smoothed;
}

export function useDocumentScanner(): UseDocumentScannerReturn {
  const [phase, setPhase] = useState<ScannerPhase>('initializing');
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null);
  const [autoProgress, setAutoProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [qualityWarnings, setQualityWarnings] = useState<QualityWarning[]>([]);

  const { status: opencvStatus, loadOpenCV } = useOpenCV();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const scannerRef = useRef<Scanner | null>(null);
  const processingCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastFrameTimeRef = useRef(0);
  const lastCornersRef = useRef<CornerPoints | null>(null);
  const smoothedCornersRef = useRef<CornerPoints | null>(null);
  const lastQualityCheckRef = useRef<number>(0);
  const qualityResultRef = useRef<QualityResult | null>(null);
  const stableStartRef = useRef<number | null>(null);
  const phaseRef = useRef<ScannerPhase>('initializing');

  const opencvReady = opencvStatus === 'ready';

  // Keep phaseRef in sync with phase state
  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

  // Start loading OpenCV immediately
  useEffect(() => {
    loadOpenCV();
  }, [loadOpenCV]);

  const stopDetectionLoop = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
  }, []);

  const drawOverlayQuad = useCallback((corners: CornerPoints, videoWidth: number, videoHeight: number, scale: number) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = videoWidth;
    canvas.height = videoHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';

    const pts = [
      corners.topLeftCorner,
      corners.topRightCorner,
      corners.bottomRightCorner,
      corners.bottomLeftCorner,
    ];

    ctx.beginPath();
    ctx.moveTo(pts[0].x * scale, pts[0].y * scale);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i].x * scale, pts[i].y * scale);
    }
    ctx.closePath();
    ctx.stroke();

    // Semi-transparent fill
    ctx.fillStyle = 'rgba(34, 197, 94, 0.08)';
    ctx.fill();

    // Corner dots
    ctx.fillStyle = '#22c55e';
    for (const pt of pts) {
      ctx.beginPath();
      ctx.arc(pt.x * scale, pt.y * scale, 6, 0, Math.PI * 2);
      ctx.fill();
    }
  }, []);

  const clearOverlay = useCallback(() => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, []);

  const startDetectionLoop = useCallback(() => {
    if (!scannerRef.current) {
      try {
        scannerRef.current = new Scanner();
      } catch {
        // jscanify init failed — continue without detection
      }
    }

    if (!processingCanvasRef.current) {
      processingCanvasRef.current = document.createElement('canvas');
    }

    const detect = (timestamp: number) => {
      if (phaseRef.current !== 'scanning') return;

      if (timestamp - lastFrameTimeRef.current < FRAME_INTERVAL) {
        rafRef.current = requestAnimationFrame(detect);
        return;
      }
      lastFrameTimeRef.current = timestamp;

      const video = videoRef.current;
      const scanner = scannerRef.current;
      const cv = (window as any).cv;

      if (!video || video.readyState < 2 || !scanner || !cv?.Mat) {
        clearOverlay();
        rafRef.current = requestAnimationFrame(detect);
        return;
      }

      const vw = video.videoWidth;
      const vh = video.videoHeight;
      if (!vw || !vh) {
        rafRef.current = requestAnimationFrame(detect);
        return;
      }

      const scale = PROCESSING_WIDTH / vw;
      const pw = PROCESSING_WIDTH;
      const ph = Math.round(vh * scale);

      const pCanvas = processingCanvasRef.current!;
      pCanvas.width = pw;
      pCanvas.height = ph;
      const pCtx = pCanvas.getContext('2d')!;
      pCtx.drawImage(video, 0, 0, pw, ph);

      let corners: CornerPoints | null = null;
      let mat: any = null;
      let contour: any = null;

      try {
        mat = cv.imread(pCanvas);
        contour = scanner.findPaperContour(mat);
        if (contour) {
          const pts = scanner.getCornerPoints(contour);
          if (pts) corners = pts;
        }

        // Run quality check periodically (every 200ms) when corners detected
        if (corners && mat && timestamp - lastQualityCheckRef.current > 200) {
          lastQualityCheckRef.current = timestamp;
          const qualityResult = scanner.checkQuality(mat, corners, pw, ph);
          qualityResultRef.current = qualityResult;
          setQualityWarnings(qualityResult.warnings);
        }
      } catch {
        // Detection error — skip frame
      } finally {
        if (mat) mat.delete();
        if (contour) contour.delete();
      }

      if (corners) {
        // Apply Kalman-like smoothing to reduce jitter in overlay
        const smoothedCorners = smoothCorners(corners, smoothedCornersRef.current, KALMAN_SMOOTHING);
        smoothedCornersRef.current = smoothedCorners;

        // Draw overlay with smoothed corners for visual stability
        drawOverlayQuad(smoothedCorners, vw, vh, 1 / scale);

        // Check if quality is acceptable for auto-capture
        const qualityOk = qualityResultRef.current?.isAcceptable ?? true;

        if (cornersStable(lastCornersRef.current, corners) && qualityOk) {
          if (!stableStartRef.current) {
            stableStartRef.current = timestamp;
          }
          const elapsed = timestamp - stableStartRef.current;
          const progress = Math.min(elapsed / AUTO_CAPTURE_DELAY_MS, 1);
          setAutoProgress(progress);

          if (progress >= 1) {
            // Auto-capture
            captureFrame(vw, vh);
            return; // Stop loop
          }
        } else {
          stableStartRef.current = timestamp;
          setAutoProgress(0);
        }
        lastCornersRef.current = corners;
      } else {
        clearOverlay();
        lastCornersRef.current = null;
        smoothedCornersRef.current = null;
        stableStartRef.current = null;
        setAutoProgress(0);
        setQualityWarnings([]);
        qualityResultRef.current = null;
      }

      rafRef.current = requestAnimationFrame(detect);
    };

    rafRef.current = requestAnimationFrame(detect);
  }, [drawOverlayQuad, clearOverlay]);

  const captureFrame = useCallback((videoWidth?: number, videoHeight?: number) => {
    const video = videoRef.current;
    if (!video) return;

    const vw = videoWidth || video.videoWidth;
    const vh = videoHeight || video.videoHeight;
    if (!vw || !vh) return;

    stopDetectionLoop();

    if (!captureCanvasRef.current) {
      captureCanvasRef.current = document.createElement('canvas');
    }

    const canvas = captureCanvasRef.current;
    const scanner = scannerRef.current;
    const cv = (window as any).cv;

    // Try perspective correction if OpenCV available
    if (scanner && cv?.Mat) {
      try {
        // Use full-res frame for extraction
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = vw;
        tempCanvas.height = vh;
        const tCtx = tempCanvas.getContext('2d')!;
        tCtx.drawImage(video, 0, 0, vw, vh);

        const result = scanner.extractPaper(tempCanvas, vw, vh);
        if (!result) throw new Error('No paper detected');
        canvas.width = result.width;
        canvas.height = result.height;
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(result, 0, 0);
      } catch {
        // Fallback: raw frame (no paper detected or extraction failed)
        canvas.width = vw;
        canvas.height = vh;
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(video, 0, 0, vw, vh);
      }
    } else {
      // No OpenCV — raw frame
      canvas.width = vw;
      canvas.height = vh;
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(video, 0, 0, vw, vh);
    }

    // Pause video (keep stream alive for retake)
    video.pause();

    const url = canvas.toDataURL('image/jpeg', 0.95);
    setCapturedImageUrl(url);
    setAutoProgress(0);
    clearOverlay();
    setPhase('captured');
  }, [stopDetectionLoop, clearOverlay]);

  const startCamera = useCallback(async () => {
    setPhase('initializing');
    setErrorMessage(null);

    try {
      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        });
      } catch {
        // Fallback: any camera
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }

      streamRef.current = stream;

      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        await video.play();
      }

      setPhase('scanning');
    } catch (err: any) {
      const msg = err?.name === 'NotAllowedError'
        ? 'Kamerazugriff wurde verweigert. Bitte erlauben Sie den Kamerazugriff in Ihren Browsereinstellungen.'
        : 'Kamera konnte nicht gestartet werden. Bitte prüfen Sie, ob eine Kamera verfügbar ist.';
      setErrorMessage(msg);
      setPhase('error');
    }
  }, []);

  // Start detection loop when phase transitions to scanning
  useEffect(() => {
    if (phase === 'scanning' && opencvReady) {
      startDetectionLoop();
    }
    return () => stopDetectionLoop();
  }, [phase, opencvReady, startDetectionLoop, stopDetectionLoop]);

  const captureManual = useCallback(() => {
    captureFrame();
  }, [captureFrame]);

  const confirmCapture = useCallback((): File | null => {
    const canvas = captureCanvasRef.current;
    if (!canvas) return null;

    // Convert to blob synchronously via toDataURL
    const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
    const byteString = atob(dataUrl.split(',')[1]);
    const mimeString = dataUrl.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
      ia[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([ab], { type: mimeString });
    const fileName = `scan_${Date.now()}.jpg`;
    return new File([blob], fileName, { type: 'image/jpeg' });
  }, []);

  const retake = useCallback(() => {
    setCapturedImageUrl(null);
    setAutoProgress(0);
    setQualityWarnings([]);
    lastCornersRef.current = null;
    smoothedCornersRef.current = null;
    stableStartRef.current = null;
    qualityResultRef.current = null;
    lastQualityCheckRef.current = 0;

    const video = videoRef.current;
    if (video && video.srcObject) {
      // Resume video playback and wait for it to be ready
      video.play().then(() => {
        // Video is playing, now set phase to trigger detection loop
        setPhase('scanning');
      }).catch(() => {
        // If play fails, still try to set scanning phase
        setPhase('scanning');
      });
    } else {
      setPhase('scanning');
    }
  }, []);

  const cleanup = useCallback(() => {
    stopDetectionLoop();

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setCapturedImageUrl(null);
    setAutoProgress(0);
    setErrorMessage(null);
    setQualityWarnings([]);
    lastCornersRef.current = null;
    smoothedCornersRef.current = null;
    stableStartRef.current = null;
    qualityResultRef.current = null;
    lastQualityCheckRef.current = 0;
    setPhase('initializing');
  }, [stopDetectionLoop]);

  return {
    phase,
    videoRef,
    overlayCanvasRef,
    capturedImageUrl,
    autoProgress,
    opencvReady,
    errorMessage,
    qualityWarnings,
    startCamera,
    captureManual,
    confirmCapture,
    retake,
    cleanup,
  };
}
