import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, Check } from 'lucide-react';

// UI Languages configuration
// Using globe icon (🌍) for Arabic and Farsi to stay neutral across diverse communities
const UI_LANGUAGES = [
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'uk', name: 'Українська', flag: '🇺🇦' },
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'pl', name: 'Polski', flag: '🇵🇱' },
  { code: 'ro', name: 'Română', flag: '🇷🇴' },
  { code: 'ar', name: 'العربية', flag: '🌍', rtl: true },
  { code: 'fa', name: 'فارسی/دری', flag: '🌍', rtl: true },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'it', name: 'Italiano', flag: '🇮🇹' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
];

const LanguageSwitcher: React.FC = () => {
  const { i18n, t } = useTranslation();
  const currentLang = i18n.language?.substring(0, 2) || 'de';
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLanguage = UI_LANGUAGES.find(l => l.code === currentLang) || UI_LANGUAGES[0];

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

  // Close dropdown on escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label={t('languageSwitcher.changeLanguage')}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white/80 shadow-sm border border-neutral-200 hover:shadow-md transition-all duration-200"
      >
        <span className="text-xl" aria-hidden="true">{currentLanguage.flag}</span>
        <span className="text-sm font-medium text-primary-700 hidden sm:inline">{currentLanguage.name}</span>
        <ChevronDown className={`w-4 h-4 text-primary-500 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-label={t('languageSwitcher.selectLanguage')}
          className="absolute right-0 top-full mt-2 bg-white rounded-xl shadow-lg border border-neutral-200 overflow-hidden z-50 min-w-[180px] animate-scale-in"
        >
          {UI_LANGUAGES.map(lang => (
            <button
              key={lang.code}
              role="option"
              aria-selected={currentLang === lang.code}
              onClick={() => handleChange(lang.code)}
              className={`flex items-center space-x-3 w-full px-4 py-2.5 hover:bg-neutral-50 transition-colors ${
                currentLang === lang.code ? 'bg-brand-50 text-brand-700' : 'text-primary-700'
              }`}
            >
              <span className="text-xl" aria-hidden="true">{lang.flag}</span>
              <span className="text-sm font-medium flex-1 text-left">{lang.name}</span>
              {currentLang === lang.code && (
                <Check className="w-4 h-4 text-brand-600" aria-hidden="true" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;
