import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

// Flag SVG components for reuse
const GermanFlag = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <clipPath id="flagClipDe">
      <circle cx="10" cy="10" r="10" />
    </clipPath>
    <g clipPath="url(#flagClipDe)">
      <rect y="0" width="20" height="7" fill="#000" />
      <rect y="7" width="20" height="6" fill="#D00" />
      <rect y="13" width="20" height="7" fill="#FFCE00" />
    </g>
  </svg>
);

const EnglishFlag = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <clipPath id="flagClipEn">
      <circle cx="10" cy="10" r="10" />
    </clipPath>
    <g clipPath="url(#flagClipEn)">
      <rect width="20" height="20" fill="#012169" />
      <path d="M0,0 L20,20 M20,0 L0,20" stroke="#fff" strokeWidth="3" />
      <path d="M0,0 L20,20 M20,0 L0,20" stroke="#C8102E" strokeWidth="1.5" />
      <path d="M10,0 V20 M0,10 H20" stroke="#fff" strokeWidth="5" />
      <path d="M10,0 V20 M0,10 H20" stroke="#C8102E" strokeWidth="3" />
    </g>
  </svg>
);

const LanguageSwitcher: React.FC = () => {
  const { i18n, t } = useTranslation();
  const currentLang = i18n.language?.substring(0, 2) || 'de';
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleChange = (lang: string) => {
    i18n.changeLanguage(lang);
    setIsOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const CurrentFlag = currentLang === 'de' ? GermanFlag : EnglishFlag;
  const OtherFlag = currentLang === 'de' ? EnglishFlag : GermanFlag;
  const otherLang = currentLang === 'de' ? 'en' : 'de';
  const otherLangLabel = currentLang === 'de' ? 'English' : 'Deutsch';

  return (
    <>
      {/* Mobile: Single flag with dropdown */}
      <div className="sm:hidden relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-haspopup="true"
          aria-label={t('languageSwitcher.changeLanguage')}
          className="w-9 h-9 rounded-full flex items-center justify-center bg-white/80 shadow-sm border border-neutral-200 transition-all duration-200 hover:shadow-md active:scale-95"
        >
          <CurrentFlag size={22} />
        </button>

        {/* Dropdown */}
        {isOpen && (
          <div className="absolute right-0 top-full mt-2 bg-white rounded-xl shadow-lg border border-neutral-200 overflow-hidden z-50 animate-scale-in">
            <button
              onClick={() => handleChange(otherLang)}
              className="flex items-center space-x-2 px-3 py-2.5 hover:bg-neutral-50 transition-colors w-full"
              aria-label={otherLangLabel}
            >
              <OtherFlag size={22} />
              <span className="text-sm font-medium text-primary-700">{otherLangLabel}</span>
            </button>
          </div>
        )}
      </div>

      {/* Desktop: Side-by-side flags */}
      <div className="hidden sm:flex items-center space-x-1">
        <button
          onClick={() => handleChange('de')}
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
            currentLang === 'de'
              ? 'ring-2 ring-brand-500 ring-offset-1 scale-110'
              : 'opacity-60 hover:opacity-100 hover:scale-105'
          }`}
          aria-label="Deutsch"
          aria-pressed={currentLang === 'de'}
        >
          <GermanFlag />
        </button>
        <button
          onClick={() => handleChange('en')}
          className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
            currentLang === 'en'
              ? 'ring-2 ring-brand-500 ring-offset-1 scale-110'
              : 'opacity-60 hover:opacity-100 hover:scale-105'
          }`}
          aria-label="English"
          aria-pressed={currentLang === 'en'}
        >
          <EnglishFlag />
        </button>
      </div>
    </>
  );
};

export default LanguageSwitcher;
