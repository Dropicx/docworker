/**
 * Shared layout for legal pages (Impressum, Datenschutz, Nutzungsbedingungen).
 * Features gradient header, dark mode support, and theme toggle.
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, BookOpen, Sun, Moon } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface LegalLayoutProps {
  title: string;
  children: React.ReactNode;
}

export const LegalLayout: React.FC<LegalLayoutProps> = ({ title, children }) => {
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const footerLinks = [
    { to: '/impressum', label: 'Impressum' },
    { to: '/datenschutz', label: 'Datenschutz' },
    { to: '/nutzungsbedingungen', label: 'Nutzungsbedingungen' },
  ];

  return (
    <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-700">
        <div className="max-w-4xl mx-auto px-3 md:px-4">
          <div className="flex items-center justify-between h-12 md:h-16">
            {/* Left: Back link */}
            <Link
              to="/"
              className="flex items-center gap-1.5 text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Zum Chat</span>
            </Link>

            {/* Center: Logo + title */}
            <div className="flex items-center gap-2 md:gap-3">
              <div className="bg-gradient-to-br from-brand-500 to-accent-500 p-1.5 md:p-2 rounded-lg shadow-soft">
                <BookOpen className="w-4 h-4 md:w-5 md:h-5 text-white" />
              </div>
              <span className="font-semibold text-neutral-900 dark:text-neutral-50 text-sm md:text-base">
                Frag die Leitlinie
              </span>
            </div>

            {/* Right: Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
              title={theme === 'light' ? 'Dunkelmodus aktivieren' : 'Hellmodus aktivieren'}
              aria-label={theme === 'light' ? 'Dunkelmodus aktivieren' : 'Hellmodus aktivieren'}
            >
              {theme === 'light' ? (
                <Moon className="w-4 h-4 md:w-5 md:h-5" />
              ) : (
                <Sun className="w-4 h-4 md:w-5 md:h-5" />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-3 md:px-4 py-6 md:py-8">
        <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-sm border border-neutral-200 dark:border-neutral-700 p-4 md:p-8">
          <h1 className="text-2xl md:text-3xl font-bold text-neutral-800 dark:text-neutral-100 mb-6">
            {title}
          </h1>
          <div className="prose prose-neutral dark:prose-invert max-w-none">
            {children}
          </div>
        </div>

        {/* Footer links */}
        <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-2">
          {footerLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`text-sm transition-colors ${
                location.pathname === to
                  ? 'text-brand-600 dark:text-brand-400 font-medium'
                  : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
};

export default LegalLayout;
