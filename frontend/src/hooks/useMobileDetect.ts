import { useState, useEffect } from 'react';

// Max width for mobile-only (phones)
const MOBILE_MAX_WIDTH = 768;
// Max width for tablets (landscape tablets can be up to ~1366px)
const TABLET_MAX_WIDTH = 1400;

function checkScannerEligibility(): boolean {
  const hasCamera = !!navigator.mediaDevices?.getUserMedia;
  const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  const viewportWidth = window.innerWidth;

  // Check user agent for tablet patterns
  const ua = navigator.userAgent.toLowerCase();
  const isTabletUA = /ipad|tablet|playbook|silk|android(?!.*mobile)/i.test(ua);
  const isIOSDevice = /iphone|ipad|ipod/.test(ua) || (navigator.platform === 'MacIntel' && hasTouch);

  // Show scanner if:
  // 1. Has camera AND touch support AND (is mobile width OR is tablet)
  // 2. Tablets: touch device with width <= 1400px (covers landscape tablets)
  // 3. Or explicitly detected as tablet via user agent
  const isMobileWidth = viewportWidth <= MOBILE_MAX_WIDTH;
  const isTabletWidth = viewportWidth <= TABLET_MAX_WIDTH;
  const isTabletDevice = hasTouch && (isTabletUA || isIOSDevice || isTabletWidth);

  return hasCamera && (isMobileWidth || isTabletDevice);
}

export function useMobileDetect() {
  const [shouldShowScanner, setShouldShowScanner] = useState(() => checkScannerEligibility());

  useEffect(() => {
    const handler = () => setShouldShowScanner(checkScannerEligibility());

    // Listen for resize and orientation changes
    window.addEventListener('resize', handler);
    window.addEventListener('orientationchange', handler);

    return () => {
      window.removeEventListener('resize', handler);
      window.removeEventListener('orientationchange', handler);
    };
  }, []);

  return { shouldShowScanner };
}
