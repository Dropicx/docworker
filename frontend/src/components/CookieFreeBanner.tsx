/**
 * Cookie-Free Notice Banner Component
 * Issue #49 - Transparent communication that HealthLingo does not use cookies
 */

import { useState, useEffect } from 'react';
import { Cookie, X, Shield } from 'lucide-react';

const BANNER_DISMISSED_KEY = 'cookieFreeBannerDismissed';

export default function CookieFreeBanner() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Check if banner was previously dismissed
    const dismissed = localStorage.getItem(BANNER_DISMISSED_KEY);
    if (!dismissed) {
      // Small delay for better UX - let the page load first
      const timer = setTimeout(() => setIsVisible(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleDismiss = () => {
    setIsVisible(false);
    localStorage.setItem(BANNER_DISMISSED_KEY, 'true');
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 animate-slide-up">
      <div className="bg-gradient-to-r from-brand-600 to-accent-600 text-white shadow-lg">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
          <div className="flex items-center justify-between gap-4">
            {/* Icon and Message */}
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="flex-shrink-0 hidden sm:flex items-center justify-center w-10 h-10 bg-white/20 rounded-full">
                <Cookie className="w-5 h-5" />
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                <Shield className="w-4 h-4 sm:hidden flex-shrink-0" />
                <div>
                  <p className="text-sm sm:text-base font-medium">
                    Keine Cookies!
                  </p>
                  <p className="text-xs sm:text-sm text-white/90 mt-0.5">
                    HealthLingo verwendet keine Cookies und speichert keine Tracking-Daten.
                  </p>
                </div>
              </div>
            </div>

            {/* Dismiss Button */}
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 p-2 hover:bg-white/20 rounded-lg transition-colors duration-200 group"
              aria-label="Banner schließen"
            >
              <X className="w-5 h-5 group-hover:scale-110 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
