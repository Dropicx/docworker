import { useState, useCallback, useRef } from 'react';

type OpenCVStatus = 'idle' | 'loading' | 'ready' | 'error';

const OPENCV_CDN_URL = 'https://docs.opencv.org/4.9.0/opencv.js';
const LOAD_TIMEOUT_MS = 30_000;

let globalStatus: OpenCVStatus = 'idle';
let globalPromise: Promise<void> | null = null;

function loadOpenCVScript(): Promise<void> {
  if (globalPromise) return globalPromise;

  globalPromise = new Promise<void>((resolve, reject) => {
    if (typeof (window as any).cv?.Mat === 'function') {
      globalStatus = 'ready';
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = OPENCV_CDN_URL;
    script.async = true;

    const timeout = setTimeout(() => {
      globalStatus = 'error';
      reject(new Error('OpenCV load timeout'));
    }, LOAD_TIMEOUT_MS);

    script.onload = () => {
      // OpenCV.js sets cv as a Module that calls onRuntimeInitialized
      const cv = (window as any).cv;
      if (cv && typeof cv.then === 'function') {
        // OpenCV 4.x uses a promise-based init
        cv.then((readyCv: any) => {
          (window as any).cv = readyCv;
          clearTimeout(timeout);
          globalStatus = 'ready';
          resolve();
        }).catch(() => {
          clearTimeout(timeout);
          globalStatus = 'error';
          reject(new Error('OpenCV init failed'));
        });
      } else if (cv?.onRuntimeInitialized !== undefined) {
        cv.onRuntimeInitialized = () => {
          clearTimeout(timeout);
          globalStatus = 'ready';
          resolve();
        };
      } else {
        // Already ready
        clearTimeout(timeout);
        globalStatus = 'ready';
        resolve();
      }
    };

    script.onerror = () => {
      clearTimeout(timeout);
      globalStatus = 'error';
      globalPromise = null;
      reject(new Error('OpenCV script load failed'));
    };

    document.head.appendChild(script);
  });

  return globalPromise;
}

export function useOpenCV() {
  const [status, setStatus] = useState<OpenCVStatus>(globalStatus);
  const loadingRef = useRef(false);

  const loadOpenCV = useCallback(async () => {
    if (globalStatus === 'ready') {
      setStatus('ready');
      return;
    }
    if (loadingRef.current) return;
    loadingRef.current = true;

    setStatus('loading');
    globalStatus = 'loading';

    try {
      await loadOpenCVScript();
      setStatus('ready');
    } catch {
      setStatus('error');
    } finally {
      loadingRef.current = false;
    }
  }, []);

  return { status, loadOpenCV };
}
