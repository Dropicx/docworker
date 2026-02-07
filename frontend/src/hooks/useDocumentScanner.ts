import { useState, useRef, useCallback, useEffect } from 'react';
import Scanner, { CornerPoints } from '../lib/jscanify';

export type ScannerPhase = 'initializing' | 'scanning' | 'captured' | 'processing' | 'error';

export interface ImageQuality {
  isBlurry: boolean;
  blurScore: number;
  brightness: number;
  contrast: number;
  isAcceptable: boolean;
}

interface Point {
  x: number;
  y: number;
}

interface UseDocumentScannerReturn {
  phase: ScannerPhase;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  displayCanvasRef: React.RefObject<HTMLCanvasElement | null>;
  capturedImageUrl: string | null;
  autoProgress: number;
  errorMessage: string | null;
  documentAligned: boolean;
  imageQuality: ImageQuality | null;
  startCamera: () => Promise<void>;
  captureManual: () => void;
  confirmCapture: () => File | null;
  retake: () => void;
  cleanup: () => void;
}

const DETECTION_FPS = 30;
const FRAME_INTERVAL = 1000 / DETECTION_FPS;
const AUTO_CAPTURE_DELAY_MS = 3000; // 3 seconds after stable detection
const A4_RATIO = 1.4142; // A4 aspect ratio (height/width)
const GUIDE_PADDING = 0.06; // 6% padding from edges
const CORNER_BRACKET_LENGTH = 100; // Length of corner bracket arms in pixels
const STABLE_FRAMES_REQUIRED = 10; // ~330ms at 30fps for stability
const CORNER_STABILITY_TOLERANCE = 15; // Pixel tolerance for corner stability

export function useDocumentScanner(): UseDocumentScannerReturn {
  const [phase, setPhase] = useState<ScannerPhase>('initializing');
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null);
  const [autoProgress, setAutoProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [documentAligned, setDocumentAligned] = useState(false);
  const [imageQuality, setImageQuality] = useState<ImageQuality | null>(null);
  const [detectedCorners, setDetectedCorners] = useState<CornerPoints | null>(null);
  const [opencvReady, setOpencvReady] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const displayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastFrameTimeRef = useRef(0);
  const stableStartRef = useRef<number | null>(null);
  const phaseRef = useRef<ScannerPhase>('initializing');
  const scannerRef = useRef<Scanner | null>(null);

  // Corner detection state refs
  const detectedCornersRef = useRef<CornerPoints | null>(null);
  const lastCornersRef = useRef<CornerPoints | null>(null);
  const stableFramesRef = useRef(0);
  const displayScaleRef = useRef(1);

  // Check OpenCV availability on mount
  useEffect(() => {
    const checkOpenCV = () => {
      const cv = (window as any).cv;
      if (cv?.Mat) {
        setOpencvReady(true);
        return true;
      }
      return false;
    };

    if (checkOpenCV()) return;

    const interval = setInterval(() => {
      if (checkOpenCV()) {
        clearInterval(interval);
      }
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // Initialize jscanify scanner
  const getScanner = useCallback(() => {
    if (!scannerRef.current) {
      scannerRef.current = new Scanner();
    }
    return scannerRef.current;
  }, []);

  // Analyze image quality (blur, brightness, contrast) - lenient blur detection
  const analyzeImageQuality = useCallback((canvas: HTMLCanvasElement): ImageQuality => {
    const ctx = canvas.getContext('2d')!;
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    // Calculate brightness and contrast
    let totalBrightness = 0;
    let minBrightness = 255;
    let maxBrightness = 0;
    const grayscale: number[] = [];

    for (let i = 0; i < data.length; i += 4) {
      const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;
      grayscale.push(gray);
      totalBrightness += gray;
      minBrightness = Math.min(minBrightness, gray);
      maxBrightness = Math.max(maxBrightness, gray);
    }

    const avgBrightness = totalBrightness / grayscale.length;
    const contrast = maxBrightness - minBrightness;

    // Calculate blur score using Laplacian variance approximation
    let laplacianSum = 0;
    const width = canvas.width;
    const height = canvas.height;

    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        const idx = y * width + x;
        const laplacian = 4 * grayscale[idx] -
          grayscale[idx - 1] - grayscale[idx + 1] -
          grayscale[idx - width] - grayscale[idx + width];
        laplacianSum += laplacian * laplacian;
      }
    }

    const blurScore = Math.sqrt(laplacianSum / ((width - 2) * (height - 2)));

    // Blur detection - threshold of 4 catches blurry images
    // Higher blurScore = sharper image, lower = blurrier
    // Skip blur check for very low-contrast images (blank paper) where it's unreliable
    const canMeasureBlur = contrast > 25;
    const isBlurry = canMeasureBlur && blurScore < 4;

    // Accept image if not severely blurry and has reasonable brightness/contrast
    const isAcceptable = !isBlurry && contrast > 20 && avgBrightness > 20 && avgBrightness < 240;

    return {
      isBlurry,
      blurScore: Math.round(blurScore * 10) / 10,
      brightness: Math.round(avgBrightness),
      contrast: Math.round(contrast),
      isAcceptable
    };
  }, []);

  // Enhance image (auto-adjust brightness/contrast)
  const enhanceImage = useCallback((canvas: HTMLCanvasElement): void => {
    const ctx = canvas.getContext('2d')!;
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    // Find min/max values for contrast stretching
    let minVal = 255;
    let maxVal = 0;

    for (let i = 0; i < data.length; i += 4) {
      const gray = (data[i] + data[i + 1] + data[i + 2]) / 3;
      minVal = Math.min(minVal, gray);
      maxVal = Math.max(maxVal, gray);
    }

    // Apply contrast stretching if needed
    const range = maxVal - minVal;
    if (range < 200 && range > 10) {
      const scale = 255 / range;
      for (let i = 0; i < data.length; i += 4) {
        data[i] = Math.min(255, Math.max(0, (data[i] - minVal) * scale));
        data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - minVal) * scale));
        data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - minVal) * scale));
      }
      ctx.putImageData(imageData, 0, 0);
    }
  }, []);

  // Calculate A4 guide frame dimensions for given video dimensions (fallback when no detection)
  const calculateA4GuideFrame = useCallback((videoWidth: number, videoHeight: number) => {
    const maxW = videoWidth * (1 - GUIDE_PADDING * 2);
    const maxH = videoHeight * (1 - GUIDE_PADDING * 2);

    let guideW: number, guideH: number;
    if (maxH / maxW > A4_RATIO) {
      guideW = maxW;
      guideH = maxW * A4_RATIO;
    } else {
      guideH = maxH;
      guideW = maxH / A4_RATIO;
    }

    const x = (videoWidth - guideW) / 2;
    const y = (videoHeight - guideH) / 2;

    return { x, y, width: guideW, height: guideH };
  }, []);

  // Check if paper is present inside the guide frame by comparing
  // average brightness inside vs outside the frame (fallback when no OpenCV)
  const checkPaperInGuide = useCallback((
    ctx: CanvasRenderingContext2D,
    guideFrame: { x: number; y: number; width: number; height: number },
    canvasWidth: number,
    canvasHeight: number
  ): boolean => {
    const { x, y, width, height } = guideFrame;
    const sampleSize = 20;
    const brightnessThreshold = 150;
    const contrastThreshold = 20;

    // Sample brightness at center of guide frame
    const centerX = Math.round(x + width / 2 - sampleSize / 2);
    const centerY = Math.round(y + height / 2 - sampleSize / 2);
    const centerData = ctx.getImageData(centerX, centerY, sampleSize, sampleSize).data;
    let centerBrightness = 0;
    for (let i = 0; i < centerData.length; i += 4) {
      centerBrightness += (centerData[i] + centerData[i + 1] + centerData[i + 2]) / 3;
    }
    centerBrightness /= (sampleSize * sampleSize);

    // Sample brightness outside the guide frame (four corners of canvas)
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

    const topLeftOut = sampleOutside(outsideOffset, outsideOffset);
    const topRightOut = sampleOutside(canvasWidth - sampleSize - outsideOffset, outsideOffset);
    const bottomLeftOut = sampleOutside(outsideOffset, canvasHeight - sampleSize - outsideOffset);
    const bottomRightOut = sampleOutside(canvasWidth - sampleSize - outsideOffset, canvasHeight - sampleSize - outsideOffset);
    const avgOutside = (topLeftOut + topRightOut + bottomLeftOut + bottomRightOut) / 4;

    const isBright = centerBrightness > brightnessThreshold;
    const hasContrast = centerBrightness - avgOutside > contrastThreshold;

    return isBright && hasContrast;
  }, []);

  // Draw static A4 guide frame with corner brackets (fallback when no detection)
  const drawGuideFrame = useCallback((
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    color: string = '#ffffff',
    dpr: number = 1
  ) => {
    const bracketLen = Math.min(CORNER_BRACKET_LENGTH * dpr, width * 0.15, height * 0.15);

    ctx.strokeStyle = color;
    ctx.lineWidth = 3 * dpr;
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
  }, []);

  // Draw detected quad (green outline when document detected)
  const drawDetectedQuad = useCallback((
    ctx: CanvasRenderingContext2D,
    corners: CornerPoints,
    offsetX: number,
    offsetY: number,
    color: string = '#22c55e',
    dpr: number = 1
  ) => {
    const { topLeftCorner: tl, topRightCorner: tr,
            bottomLeftCorner: bl, bottomRightCorner: br } = corners;

    // Apply offset for letterboxing
    const tlX = offsetX + tl.x;
    const tlY = offsetY + tl.y;
    const trX = offsetX + tr.x;
    const trY = offsetY + tr.y;
    const blX = offsetX + bl.x;
    const blY = offsetY + bl.y;
    const brX = offsetX + br.x;
    const brY = offsetY + br.y;

    // Draw quad outline
    ctx.strokeStyle = color;
    ctx.lineWidth = 3 * dpr;
    ctx.beginPath();
    ctx.moveTo(tlX, tlY);
    ctx.lineTo(trX, trY);
    ctx.lineTo(brX, brY);
    ctx.lineTo(blX, blY);
    ctx.closePath();
    ctx.stroke();

    // Draw corner markers (filled circles)
    ctx.fillStyle = color;
    for (const [cx, cy] of [[tlX, tlY], [trX, trY], [blX, blY], [brX, brY]]) {
      ctx.beginPath();
      ctx.arc(cx, cy, 8 * dpr, 0, Math.PI * 2);
      ctx.fill();
    }
  }, []);

  // Check if corners are stable (not moving much between frames)
  const cornersAreSimilar = useCallback((a: CornerPoints, b: CornerPoints, tolerance: number): boolean => {
    const dist = (p1: Point, p2: Point) => Math.hypot(p1.x - p2.x, p1.y - p2.y);
    return dist(a.topLeftCorner, b.topLeftCorner) < tolerance &&
           dist(a.topRightCorner, b.topRightCorner) < tolerance &&
           dist(a.bottomLeftCorner, b.bottomLeftCorner) < tolerance &&
           dist(a.bottomRightCorner, b.bottomRightCorner) < tolerance;
  }, []);

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

  const clearDisplayCanvas = useCallback(() => {
    const canvas = displayCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }, []);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    const displayCanvas = displayCanvasRef.current;
    if (!video || !video.videoWidth || !video.videoHeight) return;

    const vw = video.videoWidth;
    const vh = video.videoHeight;

    // Get the detected corners at time of capture
    const displayCorners = detectedCornersRef.current;
    const scale = displayScaleRef.current;
    const cv = (window as any).cv;

    stopDetectionLoop();
    setPhase('processing');
    video.pause();

    setTimeout(() => {
      let finalCanvas: HTMLCanvasElement;
      const scanner = getScanner();

      if (displayCorners && cv?.Mat) {
        // OpenCV path: capture full video frame, apply perspective transform
        const fullCanvas = document.createElement('canvas');
        fullCanvas.width = vw;
        fullCanvas.height = vh;
        const ctx = fullCanvas.getContext('2d')!;
        ctx.drawImage(video, 0, 0);

        // Scale corners from display coordinates back to video coordinates
        const videoCorners: CornerPoints = {
          topLeftCorner: {
            x: displayCorners.topLeftCorner.x / scale,
            y: displayCorners.topLeftCorner.y / scale
          },
          topRightCorner: {
            x: displayCorners.topRightCorner.x / scale,
            y: displayCorners.topRightCorner.y / scale
          },
          bottomLeftCorner: {
            x: displayCorners.bottomLeftCorner.x / scale,
            y: displayCorners.bottomLeftCorner.y / scale
          },
          bottomRightCorner: {
            x: displayCorners.bottomRightCorner.x / scale,
            y: displayCorners.bottomRightCorner.y / scale
          },
        };

        // Apply perspective transform using detected corners
        // Output at high resolution A4 size (2480x3508 = A4 at 300dpi)
        const corrected = scanner.extractPaper(fullCanvas, 2480, 3508, videoCorners);
        finalCanvas = corrected || fullCanvas;
      } else {
        // NO OpenCV: Extract guide region from VIDEO at full resolution
        // Calculate guide frame in video coordinates (not display coordinates)
        const guide = calculateA4GuideFrame(vw, vh);

        // Create high-resolution output canvas (A4 at 300dpi)
        const outputWidth = 2480;
        const outputHeight = 3508;

        const guideCanvas = document.createElement('canvas');
        guideCanvas.width = outputWidth;
        guideCanvas.height = outputHeight;
        const guideCtx = guideCanvas.getContext('2d')!;

        // Extract from video at full resolution and scale to output size
        guideCtx.drawImage(
          video,
          guide.x, guide.y, guide.width, guide.height,
          0, 0, outputWidth, outputHeight
        );
        finalCanvas = guideCanvas;
      }

      // Enhance and analyze
      enhanceImage(finalCanvas);
      const quality = analyzeImageQuality(finalCanvas);
      setImageQuality(quality);

      captureCanvasRef.current = finalCanvas;
      setCapturedImageUrl(finalCanvas.toDataURL('image/jpeg', 0.95));
      setAutoProgress(0);
      clearDisplayCanvas();
      setPhase('captured');
    }, 50);
  }, [stopDetectionLoop, clearDisplayCanvas, calculateA4GuideFrame, getScanner, enhanceImage, analyzeImageQuality]);

  const startDetectionLoop = useCallback(() => {
    const displayLoop = (timestamp: number) => {
      if (phaseRef.current !== 'scanning') return;

      if (timestamp - lastFrameTimeRef.current < FRAME_INTERVAL) {
        rafRef.current = requestAnimationFrame(displayLoop);
        return;
      }
      lastFrameTimeRef.current = timestamp;

      const video = videoRef.current;
      const displayCanvas = displayCanvasRef.current;

      if (!video || video.readyState < 2 || !displayCanvas) {
        rafRef.current = requestAnimationFrame(displayLoop);
        return;
      }

      const videoW = video.videoWidth;
      const videoH = video.videoHeight;
      if (!videoW || !videoH) {
        rafRef.current = requestAnimationFrame(displayLoop);
        return;
      }

      const ctx = displayCanvas.getContext('2d');
      if (!ctx) {
        rafRef.current = requestAnimationFrame(displayLoop);
        return;
      }

      // Get container dimensions from canvas client size
      const containerW = displayCanvas.clientWidth;
      const containerH = displayCanvas.clientHeight;

      if (!containerW || !containerH) {
        rafRef.current = requestAnimationFrame(displayLoop);
        return;
      }

      // Account for device pixel ratio for sharper rendering
      const dpr = window.devicePixelRatio || 1;
      const canvasW = Math.round(containerW * dpr);
      const canvasH = Math.round(containerH * dpr);

      // Calculate scale to fit video in container (like object-contain)
      const scale = Math.min(containerW / videoW, containerH / videoH);
      const scaledW = videoW * scale * dpr;
      const scaledH = videoH * scale * dpr;
      const offsetX = (canvasW - scaledW) / 2;
      const offsetY = (canvasH - scaledH) / 2;

      // Store scale for capture coordinate conversion (in CSS pixels, not canvas pixels)
      displayScaleRef.current = scale;

      // Set canvas resolution to match container * DPR for sharp rendering
      if (displayCanvas.width !== canvasW || displayCanvas.height !== canvasH) {
        displayCanvas.width = canvasW;
        displayCanvas.height = canvasH;
      }

      // Clear and draw black background (letterbox)
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, canvasW, canvasH);

      // Draw video frame (centered with letterbox)
      ctx.drawImage(video, offsetX, offsetY, scaledW, scaledH);

      // Real-time document detection using OpenCV
      let corners: CornerPoints | null = null;
      const cv = (window as any).cv;

      if (cv?.Mat) {
        try {
          // Create a temporary canvas at scaled size for detection
          // (detecting on display-sized canvas is faster)
          const detectCanvas = document.createElement('canvas');
          detectCanvas.width = scaledW;
          detectCanvas.height = scaledH;
          const detectCtx = detectCanvas.getContext('2d')!;
          detectCtx.drawImage(video, 0, 0, scaledW, scaledH);

          const img = cv.imread(detectCanvas);
          const scanner = getScanner();
          const contour = scanner.findPaperContour(img);

          if (contour) {
            // Get corners in display coordinates (from scaled canvas)
            corners = scanner.getCornerPoints(contour);
            contour.delete();
          }
          img.delete();
        } catch (err) {
          // OpenCV error - fall back to no detection
          corners = null;
        }
      }

      // FALLBACK: If no OpenCV or no corners detected, use brightness check
      let isAlignedByBrightness = false;
      if (!corners) {
        const guide = calculateA4GuideFrame(scaledW, scaledH);
        isAlignedByBrightness = checkPaperInGuide(
          ctx,
          {
            x: offsetX + guide.x,
            y: offsetY + guide.y,
            width: guide.width,
            height: guide.height
          },
          canvasW,
          canvasH
        );
      }

      // Track corner stability (only for OpenCV mode)
      if (corners && lastCornersRef.current) {
        const isStable = cornersAreSimilar(corners, lastCornersRef.current, CORNER_STABILITY_TOLERANCE);
        stableFramesRef.current = isStable ? stableFramesRef.current + 1 : 0;
      } else if (corners) {
        stableFramesRef.current = 1; // First detection
      } else {
        stableFramesRef.current = 0;
      }
      lastCornersRef.current = corners;

      // Update state - aligned if OpenCV found corners OR brightness check passed
      const isAligned = corners !== null || isAlignedByBrightness;
      detectedCornersRef.current = corners;
      setDetectedCorners(corners);
      setDocumentAligned(isAligned);

      // Draw overlay - simplified to two states (detected vs not detected)
      if (corners) {
        // Green when document detected via OpenCV
        drawDetectedQuad(ctx, corners, offsetX, offsetY, '#22c55e', dpr);
      } else {
        // Show static guide - green if brightness detected paper, white if not
        const guide = calculateA4GuideFrame(scaledW, scaledH);
        const guideColor = isAlignedByBrightness ? '#22c55e' : 'rgba(255, 255, 255, 0.5)';
        drawGuideFrame(
          ctx,
          offsetX + guide.x,
          offsetY + guide.y,
          guide.width,
          guide.height,
          guideColor,
          dpr
        );
      }

      // Auto-capture timer - no sharpness check (unreliable across devices)
      // For OpenCV: require corner stability. For brightness fallback: just require alignment
      const shouldCountdown = corners
        ? stableFramesRef.current >= STABLE_FRAMES_REQUIRED
        : isAlignedByBrightness;

      if (shouldCountdown) {
        if (!stableStartRef.current) {
          stableStartRef.current = timestamp;
        }

        const elapsed = timestamp - stableStartRef.current;
        const progress = Math.min(elapsed / AUTO_CAPTURE_DELAY_MS, 1);
        setAutoProgress(progress);

        if (progress >= 1) {
          captureFrame();
          return;
        }
      } else {
        stableStartRef.current = null;
        setAutoProgress(0);
      }

      rafRef.current = requestAnimationFrame(displayLoop);
    };

    rafRef.current = requestAnimationFrame(displayLoop);
  }, [captureFrame, calculateA4GuideFrame, checkPaperInGuide, drawGuideFrame, drawDetectedQuad, cornersAreSimilar, getScanner]);

  const startCamera = useCallback(async () => {
    setPhase('initializing');
    setErrorMessage(null);

    try {
      let stream: MediaStream;
      try {
        // Request high resolution
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 3840 },
            height: { ideal: 2160 },
          },
          audio: false,
        });
      } catch {
        // Fallback: just request environment camera
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' },
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
    setImageQuality(null);
    setDetectedCorners(null);
    detectedCornersRef.current = null;
    lastCornersRef.current = null;
    stableFramesRef.current = 0;
    stableStartRef.current = null;

    const video = videoRef.current;
    if (video && video.srcObject) {
      video.play().then(() => {
        setPhase('scanning');
      }).catch(() => {
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
    setImageQuality(null);
    setDetectedCorners(null);
    detectedCornersRef.current = null;
    lastCornersRef.current = null;
    stableFramesRef.current = 0;
    stableStartRef.current = null;
    setPhase('initializing');
  }, [stopDetectionLoop]);

  return {
    phase,
    videoRef,
    displayCanvasRef,
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
  };
}
