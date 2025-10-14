import React, { useState, useEffect } from 'react';
import { Globe, ChevronDown, Search } from 'lucide-react';
import ApiService from '../services/api';
import { SupportedLanguage } from '../types/api';

interface LanguageSelectorProps {
  onLanguageSelect: (language: string | null) => void;
  selectedLanguage: string | null;
  disabled?: boolean;
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  onLanguageSelect,
  selectedLanguage,
  disabled = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [languages, setLanguages] = useState<SupportedLanguage[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLanguages();
  }, []);

  const loadLanguages = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await ApiService.getAvailableLanguages();
      setLanguages(response.languages);
    } catch (error: any) {
      console.error('Fehler beim Laden der Sprachen:', error);
      setError('Sprachen konnten nicht geladen werden');
    } finally {
      setLoading(false);
    }
  };

  const filteredLanguages = languages.filter(lang =>
    lang.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    lang.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const popularLanguages = filteredLanguages.filter(lang => lang.popular);
  const otherLanguages = filteredLanguages.filter(lang => !lang.popular);

  const selectedLanguageInfo = languages.find(lang => lang.code === selectedLanguage);

  const handleLanguageSelect = (languageCode: string) => {
    if (languageCode === selectedLanguage) {
      onLanguageSelect(null); // Deselect if same language
    } else {
      onLanguageSelect(languageCode);
    }
    setIsOpen(false);
    setSearchTerm('');
  };

  if (loading) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-neutral-700">
          Übersetzung (optional)
        </label>
        <div className="w-full px-4 py-3 border border-neutral-300 rounded-xl bg-neutral-50 flex items-center justify-center">
          <div className="animate-pulse flex items-center space-x-2">
            <Globe className="w-4 h-4 text-neutral-400" />
            <span className="text-sm text-neutral-500">Sprachen werden geladen...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-neutral-700">
          Übersetzung (optional)
        </label>
        <div className="w-full px-4 py-3 border border-error-300 rounded-xl bg-error-50">
          <p className="text-sm text-error-600">{error}</p>
          <button
            onClick={loadLanguages}
            className="text-sm text-error-700 hover:text-error-800 font-medium mt-1"
          >
            Erneut versuchen
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-neutral-700">
        Übersetzung (optional)
      </label>
      <div className="relative">
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={`w-full px-4 py-3 text-left border rounded-xl transition-all duration-200 ${
            disabled
              ? 'bg-neutral-100 border-neutral-200 text-neutral-400 cursor-not-allowed'
              : isOpen
              ? 'border-brand-500 ring-2 ring-brand-100 bg-white'
              : selectedLanguage
              ? 'border-brand-300 bg-brand-50 hover:border-brand-400'
              : 'border-neutral-300 bg-white hover:border-neutral-400'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Globe className={`w-4 h-4 ${
                selectedLanguage ? 'text-brand-600' : 'text-neutral-500'
              }`} />
              <span className={`text-sm ${
                selectedLanguage ? 'text-brand-900 font-medium' : 'text-neutral-600'
              }`}>
                {selectedLanguageInfo 
                  ? selectedLanguageInfo.name 
                  : 'Sprache auswählen (optional)'
                }
              </span>
            </div>
            <ChevronDown className={`w-4 h-4 text-neutral-400 transition-transform duration-200 ${
              isOpen ? 'rotate-180' : ''
            }`} />
          </div>
        </button>

        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />
            
            {/* Dropdown */}
            <div className="absolute top-full left-0 right-0 z-50 mt-2 bg-white border border-neutral-200 rounded-xl shadow-lg max-h-80 flex flex-col">
              {/* Search */}
              <div className="p-3 border-b border-neutral-100">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neutral-400" />
                  <input
                    type="text"
                    placeholder="Sprache suchen..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 text-sm border border-neutral-200 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none"
                  />
                </div>
              </div>

              {/* Language list */}
              <div className="flex-1 overflow-y-auto">
                {/* Clear selection option */}
                {selectedLanguage && (
                  <div className="px-3 py-2 border-b border-neutral-100">
                    <button
                      onClick={() => handleLanguageSelect('')}
                      className="w-full text-left px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-50 rounded-lg transition-colors duration-150"
                    >
                      ❌ Keine Übersetzung
                    </button>
                  </div>
                )}

                {/* Popular languages */}
                {popularLanguages.length > 0 && (
                  <div>
                    <div className="px-6 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide bg-neutral-50">
                      Beliebte Sprachen
                    </div>
                    {popularLanguages.map((language) => (
                      <button
                        key={language.code}
                        onClick={() => handleLanguageSelect(language.code)}
                        className={`w-full text-left px-6 py-3 text-sm transition-colors duration-150 ${
                          selectedLanguage === language.code
                            ? 'bg-brand-50 text-brand-700 font-medium'
                            : 'text-neutral-700 hover:bg-neutral-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span>{language.name}</span>
                          <span className="text-xs text-neutral-500 font-mono">
                            {language.code}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {/* Other languages */}
                {otherLanguages.length > 0 && (
                  <div>
                    <div className="px-6 py-2 text-xs font-semibold text-neutral-500 uppercase tracking-wide bg-neutral-50">
                      Alle Sprachen
                    </div>
                    {otherLanguages.map((language) => (
                      <button
                        key={language.code}
                        onClick={() => handleLanguageSelect(language.code)}
                        className={`w-full text-left px-6 py-3 text-sm transition-colors duration-150 ${
                          selectedLanguage === language.code
                            ? 'bg-brand-50 text-brand-700 font-medium'
                            : 'text-neutral-700 hover:bg-neutral-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span>{language.name}</span>
                          <span className="text-xs text-neutral-500 font-mono">
                            {language.code}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {/* No results */}
                {filteredLanguages.length === 0 && (
                  <div className="px-6 py-4 text-center text-sm text-neutral-500">
                    Keine Sprachen gefunden für &quot;{searchTerm}&quot;
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Info text */}
      <p className="text-xs text-neutral-500">
        Optional: Wählen Sie eine Sprache, um das vereinfachte Ergebnis zusätzlich zu übersetzen.
      </p>
    </div>
  );
};

export default LanguageSelector; 