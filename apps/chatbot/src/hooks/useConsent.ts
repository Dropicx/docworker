/**
 * Hook for managing user consent state.
 * Persists consent to localStorage with timestamp.
 */

import { useState, useCallback, useEffect } from 'react';

interface ConsentData {
  accepted: boolean;
  timestamp: string;
}

const STORAGE_KEY = 'fragdieleitlinie_consent';

export const useConsent = () => {
  const [hasConsented, setHasConsented] = useState<boolean | null>(null);
  const [consentData, setConsentData] = useState<ConsentData | null>(null);

  // Check localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data: ConsentData = JSON.parse(stored);
        if (data.accepted) {
          setHasConsented(true);
          setConsentData(data);
        } else {
          setHasConsented(false);
        }
      } else {
        setHasConsented(false);
      }
    } catch {
      setHasConsented(false);
    }
  }, []);

  const acceptConsent = useCallback(() => {
    const data: ConsentData = {
      accepted: true,
      timestamp: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setConsentData(data);
    setHasConsented(true);
  }, []);

  const revokeConsent = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setConsentData(null);
    setHasConsented(false);
  }, []);

  return {
    hasConsented,
    consentData,
    acceptConsent,
    revokeConsent,
    isLoading: hasConsented === null,
  };
};

export default useConsent;
