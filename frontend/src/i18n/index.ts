import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import deCommon from './locales/de/common.json';
import enCommon from './locales/en/common.json';
import deLegal from './locales/de/legal.json';
import enLegal from './locales/en/legal.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { common: deCommon, legal: deLegal },
      en: { common: enCommon, legal: enLegal },
    },
    fallbackLng: 'de',
    defaultNS: 'common',
    ns: ['common', 'legal'],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'ui_language',
      caches: ['localStorage'],
    },
  });

// Set document language on init and on change
document.documentElement.lang = i18n.language?.substring(0, 2) || 'de';
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng.substring(0, 2);
});

export default i18n;
