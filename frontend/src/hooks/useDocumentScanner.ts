import { useState, useRef, useCallback, useEffect } from 'react';

export type ScannerPhase = 'initializing' | 'scanning' | 'captured' | 'error';

interface UseDocumentScannerReturn {
  phase: ScannerPhase;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  overlayCanvasRef: React.RefObject<HTMLCanvasElement | null>;
  capturedImageUrl: string | null;
  autoProgress: number;
  errorMessage: string | null;
  documentAligned: boolean;
  startCamera: () => Promise<void>;
  captureManual: () => void;
  confirmCapture: () => File | null;
  retake: () => void;
  cleanup: () => void;
}

const DETECTION_FPS = 30;
const FRAME_INTERVAL = 1000 / DETECTION_FPS;
const AUTO_CAPTURE_DELAY_MS = 4000; // 4 seconds after alignment detected
const PROCESSING_WIDTH = 640;
const A4_RATIO = 1.4142; // A4 aspect ratio (height/width)
const GUIDE_PADDING = 0.06; // 6% padding from edges
const CORNER_BRACKET_LENGTH = 70; // Length of corner bracket arms in pixels

export function useDocumentScanner(): UseDocumentScannerReturn {
  const [phase, setPhase] = useState<ScannerPhase>('initializing');
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null);
  const [autoProgress, setAutoProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [documentAligned, setDocumentAligned] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const processingCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastFrameTimeRef = useRef(0);
  const stableStartRef = useRef<number | null>(null);
  const phaseRef = useRef<ScannerPhase>('initializing');

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

  // Check if paper is present inside the guide frame by comparing
  // average brightness inside vs outside the frame
  const checkPaperInGuide = useCallback((
    ctx: CanvasRenderingContext2D,
    guideFrame: { x: number; y: number; width: number; height: number },
    canvasWidth: number,
    canvasHeight: number
  ): boolean => {
    const { x, y, width, height } = guideFrame;
    const sampleSize = 20; // Sample area size
    const brightnessThreshold = 150; // Paper should be bright (white)
    const contrastThreshold = 20; // Difference between inside and outside

    // Sample brightness at center of guide frame (should be paper = bright)
    const centerX = Math.round(x + width / 2 - sampleSize / 2);
    const centerY = Math.round(y + height / 2 - sampleSize / 2);
    const centerData = ctx.getImageData(centerX, centerY, sampleSize, sampleSize).data;
    let centerBrightness = 0;
    for (let i = 0; i < centerData.length; i += 4) {
      centerBrightness += (centerData[i] + centerData[i + 1] + centerData[i + 2]) / 3;
    }
    centerBrightness /= (sampleSize * sampleSize);

    // Sample brightness outside the guide frame (corners of the video)
    const outsideOffset = 10;
    const sampleOutside = (sx: number, sy: number): number => {
      const clampedX = Math.max(0, Math.min(sx, canvasWidth - sampleSize));
      const clampedY = Math.max(0, Math.min(sy, canvasHeight - sampleSize));
      const data = ctx.getImageData(clampedX, clampedY, sampleSize, sampleSize).data;
      let brightness = 0;
      for (let i = 0; i < data.length; i += 4) {
        brightness += (data[i] + data[i + 1] + data[i + 2]) / 3;
      }
      return brightness / (sampleSize * sampleSize);
    };

    // Sample at corners outside the guide
    const topLeftOut = sampleOutside(outsideOffset, outsideOffset);
    const topRightOut = sampleOutside(canvasWidth - sampleSize - outsideOffset, outsideOffset);
    const bottomLeftOut = sampleOutside(outsideOffset, canvasHeight - sampleSize - outsideOffset);
    const bottomRightOut = sampleOutside(canvasWidth - sampleSize - outsideOffset, canvasHeight - sampleSize - outsideOffset);
    const avgOutside = (topLeftOut + topRightOut + bottomLeftOut + bottomRightOut) / 4;

    // Paper detected if:
    // 1. Center is bright enough (paper is white/light)
    // 2. Center is brighter than outside (contrast with background)
    const isBright = centerBrightness > brightnessThreshold;
    const hasContrast = centerBrightness - avgOutside > contrastThreshold;

    return isBright && hasContrast;
  }, []);

  // Draw A4 guide frame with corner brackets
  const drawA4Guide = useCallback((ctx: CanvasRenderingContext2D, videoWidth: number, videoHeight: number) => {
    const guide = calculateA4GuideFrame(videoWidth, videoHeight);
    const { x, y, width, height } = guide;
    const bracketLen = Math.min(CORNER_BRACKET_LENGTH, width * 0.15, height * 0.15);

    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 8;
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

    // Draw corner markers (circles)
    ctx.fillStyle = '#ffffff';
    const markerRadius = 10;
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

  const stopDetectionLoop = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
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

    // Always crop to the A4 guide frame region - this is what the user aligned to
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

    // Pause video (keep stream alive for retake)
    video.pause();

    const url = canvas.toDataURL('image/jpeg', 0.98);
    setCapturedImageUrl(url);
    setAutoProgress(0);
    clearOverlay();
    setPhase('captured');
  }, [stopDetectionLoop, clearOverlay, calculateA4GuideFrame]);

  const startDetectionLoop = useCallback(() => {
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

      if (!video || video.readyState < 2) {
        rafRef.current = requestAnimationFrame(detect);
        return;
      }

      const vw = video.videoWidth;
      const vh = video.videoHeight;
      if (!vw || !vh) {
        rafRef.current = requestAnimationFrame(detect);
        return;
      }

      // Calculate guide frame for this video size
      const guideFrame = calculateA4GuideFrame(vw, vh);

      // Draw video frame to processing canvas for edge analysis
      const pCanvas = processingCanvasRef.current!;
      pCanvas.width = vw;
      pCanvas.height = vh;
      const pCtx = pCanvas.getContext('2d')!;
      pCtx.drawImage(video, 0, 0, vw, vh);

      // Check if paper is present inside the guide frame
      const isAligned = checkPaperInGuide(pCtx, guideFrame, vw, vh);

      // Draw the A4 guide frame with color based on alignment
      const overlayCanvas = overlayCanvasRef.current;
      const overlayCtx = overlayCanvas?.getContext('2d');
      if (overlayCanvas && overlayCtx) {
        overlayCanvas.width = vw;
        overlayCanvas.height = vh;
        overlayCtx.clearRect(0, 0, vw, vh);

        // Draw guide frame - green when aligned, white when not
        const { x, y, width, height } = guideFrame;
        const bracketLen = Math.min(CORNER_BRACKET_LENGTH, width * 0.15, height * 0.15);
        const color = isAligned ? '#22c55e' : '#ffffff';

        overlayCtx.strokeStyle = color;
        overlayCtx.lineWidth = 6;
        overlayCtx.lineCap = 'round';

        // Top-left corner bracket
        overlayCtx.beginPath();
        overlayCtx.moveTo(x, y + bracketLen);
        overlayCtx.lineTo(x, y);
        overlayCtx.lineTo(x + bracketLen, y);
        overlayCtx.stroke();

        // Top-right corner bracket
        overlayCtx.beginPath();
        overlayCtx.moveTo(x + width - bracketLen, y);
        overlayCtx.lineTo(x + width, y);
        overlayCtx.lineTo(x + width, y + bracketLen);
        overlayCtx.stroke();

        // Bottom-right corner bracket
        overlayCtx.beginPath();
        overlayCtx.moveTo(x + width, y + height - bracketLen);
        overlayCtx.lineTo(x + width, y + height);
        overlayCtx.lineTo(x + width - bracketLen, y + height);
        overlayCtx.stroke();

        // Bottom-left corner bracket
        overlayCtx.beginPath();
        overlayCtx.moveTo(x + bracketLen, y + height);
        overlayCtx.lineTo(x, y + height);
        overlayCtx.lineTo(x, y + height - bracketLen);
        overlayCtx.stroke();

        // Corner markers
        overlayCtx.fillStyle = color;
        const markerRadius = 10;
        const corners = [
          { cx: x, cy: y },
          { cx: x + width, cy: y },
          { cx: x + width, cy: y + height },
          { cx: x, cy: y + height },
        ];
        for (const corner of corners) {
          overlayCtx.beginPath();
          overlayCtx.arc(corner.cx, corner.cy, markerRadius, 0, Math.PI * 2);
          overlayCtx.fill();
        }
      }

      // Update alignment state
      setDocumentAligned(isAligned);

      // Auto-capture timer - only runs when paper edges detected at guide frame
      if (isAligned) {
        if (!stableStartRef.current) {
          stableStartRef.current = timestamp;
        }

        const elapsed = timestamp - stableStartRef.current;
        const progress = Math.min(elapsed / AUTO_CAPTURE_DELAY_MS, 1);
        setAutoProgress(progress);

        if (progress >= 1) {
          // Auto-capture using the A4 guide frame
          captureFrame(vw, vh);
          return; // Stop loop
        }
      } else {
        // Reset timer when not aligned
        stableStartRef.current = null;
        setAutoProgress(0);
      }

      rafRef.current = requestAnimationFrame(detect);
    };

    rafRef.current = requestAnimationFrame(detect);
  }, [captureFrame, calculateA4GuideFrame, checkPaperInGuide]);

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
    if (phase === 'scanning') {
      startDetectionLoop();
    }
    return () => stopDetectionLoop();
  }, [phase, startDetectionLoop, stopDetectionLoop]);

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
    setDocumentAligned(false);
    stableStartRef.current = null;

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
    setDocumentAligned(false);
    stableStartRef.current = null;
    setPhase('initializing');
  }, [stopDetectionLoop]);

  return {
    phase,
    videoRef,
    overlayCanvasRef,
    capturedImageUrl,
    autoProgress,
    errorMessage,
    documentAligned,
    startCamera,
    captureManual,
    confirmCapture,
    retake,
    cleanup,
  };
}
