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
const A4_RATIO = 1.4142; // A4 aspect ratio (height/width)
const GUIDE_PADDING = 0.08; // 8% padding from edges
const CORNER_BRACKET_LENGTH = 30; // Length of corner bracket arms in pixels

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

  // Calculate A4 guide frame dimensions for given video dimensions
  const calculateA4GuideFrame = useCallback((videoWidth: number, videoHeight: number) => {
    const maxW = videoWidth * (1 - GUIDE_PADDING * 2);
    const maxH = videoHeight * (1 - GUIDE_PADDING * 2);

    let guideW: number, guideH: number;
    // A4 is portrait (taller than wide), so height = width * A4_RATIO
    if (maxH / maxW > A4_RATIO) {
      // Width-constrained
      guideW = maxW;
      guideH = maxW * A4_RATIO;
    } else {
      // Height-constrained
      guideH = maxH;
      guideW = maxH / A4_RATIO;
    }

    const x = (videoWidth - guideW) / 2;
    const y = (videoHeight - guideH) / 2;

    return { x, y, width: guideW, height: guideH };
  }, []);

  // Draw A4 guide frame with corner brackets
  const drawA4Guide = useCallback((ctx: CanvasRenderingContext2D, videoWidth: number, videoHeight: number) => {
    const guide = calculateA4GuideFrame(videoWidth, videoHeight);
    const { x, y, width, height } = guide;
    const bracketLen = Math.min(CORNER_BRACKET_LENGTH, width * 0.1, height * 0.1);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';

    // Top-left corner bracket
    ctx.beginPath();
    ctx.moveTo(x, y + bracketLen);
    ctx.lineTo(x, y);
    ctx.lineTo(x + bracketLen, y);
    ctx.stroke();

    // Top-right corner bracket
    ctx.beginPath();
    ctx.moveTo(x + width - bracketLen, y);
    ctx.lineTo(x + width, y);
    ctx.lineTo(x + width, y + bracketLen);
    ctx.stroke();

    // Bottom-right corner bracket
    ctx.beginPath();
    ctx.moveTo(x + width, y + height - bracketLen);
    ctx.lineTo(x + width, y + height);
    ctx.lineTo(x + width - bracketLen, y + height);
    ctx.stroke();

    // Bottom-left corner bracket
    ctx.beginPath();
    ctx.moveTo(x + bracketLen, y + height);
    ctx.lineTo(x, y + height);
    ctx.lineTo(x, y + height - bracketLen);
    ctx.stroke();

    // Draw small corner markers (circles)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
    const markerRadius = 5;
    const corners = [
      { cx: x, cy: y },
      { cx: x + width, cy: y },
      { cx: x + width, cy: y + height },
      { cx: x, cy: y + height },
    ];
    for (const corner of corners) {
      ctx.beginPath();
      ctx.arc(corner.cx, corner.cy, markerRadius, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [calculateA4GuideFrame]);

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

  const drawOverlayQuad = useCallback((ctx: CanvasRenderingContext2D, corners: CornerPoints, scale: number) => {
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

  const clearOverlay = useCallback((drawGuide: boolean = false, videoWidth?: number, videoHeight?: number) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (videoWidth && videoHeight) {
      canvas.width = videoWidth;
      canvas.height = videoHeight;
    }
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw A4 guide frame if requested
    if (drawGuide && videoWidth && videoHeight) {
      drawA4Guide(ctx, videoWidth, videoHeight);
    }
  }, [drawA4Guide]);

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

      // Always prepare canvas and draw A4 guide frame first (persistent)
      const overlayCanvas = overlayCanvasRef.current;
      if (overlayCanvas) {
        overlayCanvas.width = vw;
        overlayCanvas.height = vh;
        const overlayCtx = overlayCanvas.getContext('2d');
        if (overlayCtx) {
          overlayCtx.clearRect(0, 0, vw, vh);
          // Draw A4 guide frame (always visible)
          drawA4Guide(overlayCtx, vw, vh);

          // Draw detected corners on top (when available)
          if (corners) {
            // Apply Kalman-like smoothing to reduce jitter in overlay
            const smoothedCorners = smoothCorners(corners, smoothedCornersRef.current, KALMAN_SMOOTHING);
            smoothedCornersRef.current = smoothedCorners;

            // Draw overlay with smoothed corners for visual stability
            drawOverlayQuad(overlayCtx, smoothedCorners, 1 / scale);
          }
        }
      }

      if (corners) {
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
        // No corners detected - guide is already drawn above
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
  }, [drawOverlayQuad, drawA4Guide]);

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
        // Fallback: crop to A4 guide frame region
        const guide = calculateA4GuideFrame(vw, vh);

        // Create temp canvas for full frame
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = vw;
        tempCanvas.height = vh;
        const tCtx = tempCanvas.getContext('2d')!;
        tCtx.drawImage(video, 0, 0, vw, vh);

        // Set output dimensions to A4 ratio
        const outputWidth = Math.round(guide.width);
        const outputHeight = Math.round(guide.height);
        canvas.width = outputWidth;
        canvas.height = outputHeight;
        const ctx = canvas.getContext('2d')!;

        // Crop to guide frame region
        ctx.drawImage(
          tempCanvas,
          guide.x, guide.y, guide.width, guide.height,
          0, 0, outputWidth, outputHeight
        );
      }
    } else {
      // No OpenCV — crop to A4 guide frame region
      const guide = calculateA4GuideFrame(vw, vh);

      const tempCanvas = document.createElement('canvas');
      tempCanvas.width = vw;
      tempCanvas.height = vh;
      const tCtx = tempCanvas.getContext('2d')!;
      tCtx.drawImage(video, 0, 0, vw, vh);

      const outputWidth = Math.round(guide.width);
      const outputHeight = Math.round(guide.height);
      canvas.width = outputWidth;
      canvas.height = outputHeight;
      const ctx = canvas.getContext('2d')!;

      ctx.drawImage(
        tempCanvas,
        guide.x, guide.y, guide.width, guide.height,
        0, 0, outputWidth, outputHeight
      );
    }

    // Pause video (keep stream alive for retake)
    video.pause();

    const url = canvas.toDataURL('image/jpeg', 0.98);
    setCapturedImageUrl(url);
    setAutoProgress(0);
    clearOverlay();
    setPhase('captured');
  }, [stopDetectionLoop, clearOverlay, calculateA4GuideFrame]);

  const startCamera = useCallback(async () => {
    setPhase('initializing');
    setErrorMessage(null);

    try {
      let stream: MediaStream;
      try {
        // Request maximum resolution - 4K or higher if available
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment',
            width: { ideal: 4096, min: 1920 },
            height: { ideal: 2160, min: 1080 },
          },
          audio: false,
        });
      } catch {
        // Fallback: try without min constraints
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 3840 }, height: { ideal: 2160 } },
            audio: false,
          });
        } catch {
          // Final fallback: any camera
          stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        }
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
    const dataUrl = canvas.toDataURL('image/jpeg', 0.98);
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
