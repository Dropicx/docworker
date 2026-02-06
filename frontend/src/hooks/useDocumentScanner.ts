import { useState, useRef, useCallback, useEffect } from 'react';
import Scanner from '../lib/jscanify';

export type ScannerPhase = 'initializing' | 'scanning' | 'captured' | 'processing' | 'error';

export interface ImageQuality {
  isBlurry: boolean;
  blurScore: number;
  brightness: number;
  contrast: number;
  isAcceptable: boolean;
}

interface DisplayMapping {
  offsetX: number;
  offsetY: number;
  scale: number;
  scaledW: number;
  scaledH: number;
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
const AUTO_CAPTURE_DELAY_MS = 3000; // 3 seconds after alignment detected
const A4_RATIO = 1.4142; // A4 aspect ratio (height/width)
const GUIDE_PADDING = 0.06; // 6% padding from edges
const CORNER_BRACKET_LENGTH = 100; // Length of corner bracket arms in pixels

export function useDocumentScanner(): UseDocumentScannerReturn {
  const [phase, setPhase] = useState<ScannerPhase>('initializing');
  const [capturedImageUrl, setCapturedImageUrl] = useState<string | null>(null);
  const [autoProgress, setAutoProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [documentAligned, setDocumentAligned] = useState(false);
  const [imageQuality, setImageQuality] = useState<ImageQuality | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const displayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const captureCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const lastFrameTimeRef = useRef(0);
  const stableStartRef = useRef<number | null>(null);
  const phaseRef = useRef<ScannerPhase>('initializing');
  const displayMappingRef = useRef<DisplayMapping>({ offsetX: 0, offsetY: 0, scale: 1, scaledW: 0, scaledH: 0 });
  const scannerRef = useRef<Scanner | null>(null);

  // Initialize jscanify scanner
  const getScanner = useCallback(() => {
    if (!scannerRef.current) {
      scannerRef.current = new Scanner();
    }
    return scannerRef.current;
  }, []);

  // Analyze image quality (blur, brightness, contrast)
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
    // Higher score = sharper image, lower score = blurry
    let laplacianSum = 0;
    const width = canvas.width;
    const height = canvas.height;

    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        const idx = y * width + x;
        // Laplacian kernel: center * 4 - neighbors
        const laplacian = 4 * grayscale[idx] -
          grayscale[idx - 1] - grayscale[idx + 1] -
          grayscale[idx - width] - grayscale[idx + width];
        laplacianSum += laplacian * laplacian;
      }
    }

    const blurScore = Math.sqrt(laplacianSum / ((width - 2) * (height - 2)));
    const isBlurry = blurScore < 15; // Threshold for blur detection

    // Image is acceptable if not too blurry and has decent contrast
    const isAcceptable = !isBlurry && contrast > 50 && avgBrightness > 40 && avgBrightness < 220;

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
    if (range < 200 && range > 10) { // Only enhance if contrast is low
      const scale = 255 / range;
      for (let i = 0; i < data.length; i += 4) {
        data[i] = Math.min(255, Math.max(0, (data[i] - minVal) * scale));     // R
        data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - minVal) * scale)); // G
        data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - minVal) * scale)); // B
      }
      ctx.putImageData(imageData, 0, 0);
    }

    // Slight sharpening using unsharp mask approximation
    // (simplified version - applies a subtle sharpen)
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = canvas.width;
    tempCanvas.height = canvas.height;
    const tempCtx = tempCanvas.getContext('2d')!;

    // Draw slightly blurred version
    tempCtx.filter = 'blur(1px)';
    tempCtx.drawImage(canvas, 0, 0);
    tempCtx.filter = 'none';

    // Blend original with difference for sharpening
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.drawImage(canvas, 0, 0);
  }, []);

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

  // Draw A4 guide frame with corner brackets at specified position
  const drawGuideFrame = useCallback((
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    color: string = '#ffffff'
  ) => {
    const bracketLen = Math.min(CORNER_BRACKET_LENGTH, width * 0.15, height * 0.15);

    ctx.strokeStyle = color;
    ctx.lineWidth = 4;
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
    ctx.fillStyle = color;
    const markerRadius = 6;
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

  // Apply perspective correction using jscanify if OpenCV is available
  const applyPerspectiveCorrection = useCallback((canvas: HTMLCanvasElement): HTMLCanvasElement => {
    const cv = (window as any).cv;
    if (!cv?.Mat) {
      console.log('OpenCV not available, skipping perspective correction');
      return canvas;
    }

    try {
      const scanner = getScanner();

      // Try to extract and correct the paper
      const corrected = scanner.extractPaper(canvas, canvas.width, canvas.height);

      if (corrected) {
        console.log('Perspective correction applied');
        return corrected;
      }
    } catch (err) {
      console.warn('Perspective correction failed:', err);
    }

    return canvas;
  }, [getScanner]);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    const vw = video.videoWidth;
    const vh = video.videoHeight;

    console.log('Capture - video dimensions:', vw, 'x', vh);

    if (!vw || !vh) {
      console.error('Video dimensions not available');
      return;
    }

    stopDetectionLoop();
    setPhase('processing');

    // Get the display mapping to calculate correct capture region
    const { scale, scaledW, scaledH } = displayMappingRef.current;

    // Calculate guide frame in SCALED (display) coordinates
    const displayGuide = calculateA4GuideFrame(scaledW, scaledH);

    // Map back to VIDEO coordinates for full-resolution capture
    const videoGuide = {
      x: displayGuide.x / scale,
      y: displayGuide.y / scale,
      width: displayGuide.width / scale,
      height: displayGuide.height / scale
    };

    console.log('Display guide:', displayGuide);
    console.log('Video guide (mapped):', videoGuide);

    // Create capture canvas at full video resolution for the guide region
    const captureCanvas = document.createElement('canvas');
    const outputWidth = Math.round(videoGuide.width);
    const outputHeight = Math.round(videoGuide.height);
    captureCanvas.width = outputWidth;
    captureCanvas.height = outputHeight;
    const ctx = captureCanvas.getContext('2d')!;

    // Draw the guide frame region from video at full resolution
    ctx.drawImage(
      video,
      videoGuide.x, videoGuide.y, videoGuide.width, videoGuide.height,
      0, 0, outputWidth, outputHeight
    );

    // Pause video (keep stream alive for retake)
    video.pause();

    // Process asynchronously to allow UI update
    setTimeout(() => {
      // Apply perspective correction if available
      let finalCanvas = applyPerspectiveCorrection(captureCanvas);

      // Apply image enhancement
      enhanceImage(finalCanvas);

      // Analyze quality
      const quality = analyzeImageQuality(finalCanvas);
      setImageQuality(quality);

      // Store for confirmation
      captureCanvasRef.current = finalCanvas;

      const url = finalCanvas.toDataURL('image/jpeg', 0.95);
      console.log('Captured image dimensions:', finalCanvas.width, 'x', finalCanvas.height);
      setCapturedImageUrl(url);
      setAutoProgress(0);
      clearDisplayCanvas();
      setPhase('captured');
    }, 50);
  }, [stopDetectionLoop, clearDisplayCanvas, calculateA4GuideFrame, analyzeImageQuality, enhanceImage, applyPerspectiveCorrection]);

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

      // Calculate scale to fit video in container (like object-contain)
      const scale = Math.min(containerW / videoW, containerH / videoH);
      const scaledW = videoW * scale;
      const scaledH = videoH * scale;
      const offsetX = (containerW - scaledW) / 2;
      const offsetY = (containerH - scaledH) / 2;

      // Set canvas resolution to match container (for crisp rendering)
      if (displayCanvas.width !== containerW || displayCanvas.height !== containerH) {
        displayCanvas.width = containerW;
        displayCanvas.height = containerH;
      }

      // Clear and draw black background (letterbox)
      ctx.fillStyle = '#000';
      ctx.fillRect(0, 0, containerW, containerH);

      // Draw video frame (centered with letterbox)
      ctx.drawImage(video, offsetX, offsetY, scaledW, scaledH);

      // Calculate guide frame in DISPLAY coordinates (within the scaled video area)
      const guide = calculateA4GuideFrame(scaledW, scaledH);

      // Check if paper is present using the displayed region
      // Sample from the canvas at display coordinates
      const isAligned = checkPaperInGuide(
        ctx,
        {
          x: offsetX + guide.x,
          y: offsetY + guide.y,
          width: guide.width,
          height: guide.height
        },
        containerW,
        containerH
      );

      // Draw guide frame at DISPLAY coordinates (offset by video position)
      const guideColor = isAligned ? '#22c55e' : '#ffffff';
      drawGuideFrame(
        ctx,
        offsetX + guide.x,
        offsetY + guide.y,
        guide.width,
        guide.height,
        guideColor
      );

      // Store mapping for capture (so we can map back to video coordinates)
      displayMappingRef.current = { offsetX, offsetY, scale, scaledW, scaledH };

      // Update alignment state
      setDocumentAligned(isAligned);

      // Auto-capture timer
      if (isAligned) {
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
  }, [captureFrame, calculateA4GuideFrame, checkPaperInGuide, drawGuideFrame]);

  const startCamera = useCallback(async () => {
    setPhase('initializing');
    setErrorMessage(null);

    try {
      let stream: MediaStream;
      try {
        // Request high resolution without forcing aspect ratio - let device choose best fit
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'environment' },
            width: { ideal: 1920 },
            height: { ideal: 1920 }, // Square ideal lets device pick best orientation
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
    setImageQuality(null);
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
    setImageQuality(null);
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
