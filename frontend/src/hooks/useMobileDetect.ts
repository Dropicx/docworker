import { useState, useEffect } from 'react';

const MOBILE_MAX_WIDTH = '(max-width: 1024px)';

function checkScannerEligibility(): boolean {
  const hasCamera = !!navigator.mediaDevices?.getUserMedia;
  const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  const isNarrowViewport = window.matchMedia(MOBILE_MAX_WIDTH).matches;
  return hasCamera && hasTouch && isNarrowViewport;
}

export function useMobileDetect() {
  const [shouldShowScanner, setShouldShowScanner] = useState(() => checkScannerEligibility());

  useEffect(() => {
    const mql = window.matchMedia(MOBILE_MAX_WIDTH);
    const handler = () => setShouldShowScanner(checkScannerEligibility());
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, []);

  return { shouldShowScanner };
}
