import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// Existing languages
import deCommon from './locales/de/common.json';
import enCommon from './locales/en/common.json';
import deLegal from './locales/de/legal.json';
import enLegal from './locales/en/legal.json';

// New languages for migrant support
import ukCommon from './locales/uk/common.json';
import ukLegal from './locales/uk/legal.json';
import ruCommon from './locales/ru/common.json';
import ruLegal from './locales/ru/legal.json';
import arCommon from './locales/ar/common.json';
import arLegal from './locales/ar/legal.json';
import faCommon from './locales/fa/common.json';
import faLegal from './locales/fa/legal.json';
import frCommon from './locales/fr/common.json';
import frLegal from './locales/fr/legal.json';
import itCommon from './locales/it/common.json';
import itLegal from './locales/it/legal.json';
import esCommon from './locales/es/common.json';
import esLegal from './locales/es/legal.json';
import trCommon from './locales/tr/common.json';
import trLegal from './locales/tr/legal.json';
import plCommon from './locales/pl/common.json';
import plLegal from './locales/pl/legal.json';
import roCommon from './locales/ro/common.json';
import roLegal from './locales/ro/legal.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { common: deCommon, legal: deLegal },
      en: { common: enCommon, legal: enLegal },
      uk: { common: ukCommon, legal: ukLegal },
      ru: { common: ruCommon, legal: ruLegal },
      ar: { common: arCommon, legal: arLegal },
      fa: { common: faCommon, legal: faLegal },
      fr: { common: frCommon, legal: frLegal },
      it: { common: itCommon, legal: itLegal },
      es: { common: esCommon, legal: esLegal },
      tr: { common: trCommon, legal: trLegal },
      pl: { common: plCommon, legal: plLegal },
      ro: { common: roCommon, legal: roLegal },
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

// Set document language and direction on init and on change
const rtlLanguages = ['ar', 'fa'];
const setDocumentLanguage = (lng: string) => {
  const lang = lng.substring(0, 2);
  document.documentElement.lang = lang;
  document.documentElement.dir = rtlLanguages.includes(lang) ? 'rtl' : 'ltr';
};

setDocumentLanguage(i18n.language || 'de');
i18n.on('languageChanged', setDocumentLanguage);

export default i18n;
