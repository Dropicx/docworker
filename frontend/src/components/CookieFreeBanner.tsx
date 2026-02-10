/**
 * Essential Cookies Notice Banner Component
 * Issue #49 - Transparent communication about essential cookies (TDDDG § 25 Abs. 2 Nr. 2 compliant)
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Cookie, Check, Shield } from 'lucide-react';

const BANNER_DISMISSED_KEY = 'cookieFreeBannerDismissed';

export default function CookieFreeBanner() {
  const { t } = useTranslation();
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

  const handleAccept = () => {
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
            <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
              <div className="flex-shrink-0 hidden sm:flex items-center justify-center w-10 h-10 bg-white/20 rounded-full">
                <Cookie className="w-5 h-5" />
              </div>
              <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                <Shield className="w-4 h-4 sm:hidden flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm sm:text-base font-medium">{t('cookieFree.title')}</p>
                  <p className="text-xs sm:text-sm text-white/90 mt-0.5">
                    {t('cookieFree.description')}{' '}
                    <Link
                      to="/datenschutz"
                      className="underline hover:text-white transition-colors"
                    >
                      {t('cookieFree.privacyLink')}
                    </Link>
                  </p>
                </div>
              </div>
            </div>

            {/* Accept Button */}
            <button
              onClick={handleAccept}
              className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors duration-200 text-sm font-medium"
            >
              <Check className="w-4 h-4" />
              <span className="hidden sm:inline">{t('cookieFree.accept')}</span>
              <span className="sm:hidden">OK</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
