import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const currentLang = i18n.language?.substring(0, 2) || 'de';

  const handleChange = (lang: string) => {
    i18n.changeLanguage(lang);
  };

  return (
    <div className="flex items-center space-x-1">
      <button
        onClick={() => handleChange('de')}
        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
          currentLang === 'de'
            ? 'ring-2 ring-brand-500 ring-offset-1 scale-110'
            : 'opacity-60 hover:opacity-100 hover:scale-105'
        }`}
        aria-label="Deutsch"
        title="Deutsch"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
          <clipPath id="flagClipDe">
            <circle cx="10" cy="10" r="10" />
          </clipPath>
          <g clipPath="url(#flagClipDe)">
            <rect y="0" width="20" height="7" fill="#000" />
            <rect y="7" width="20" height="6" fill="#D00" />
            <rect y="13" width="20" height="7" fill="#FFCE00" />
          </g>
        </svg>
      </button>
      <button
        onClick={() => handleChange('en')}
        className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 ${
          currentLang === 'en'
            ? 'ring-2 ring-brand-500 ring-offset-1 scale-110'
            : 'opacity-60 hover:opacity-100 hover:scale-105'
        }`}
        aria-label="English"
        title="English"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
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
      </button>
    </div>
  );
};

export default LanguageSwitcher;
