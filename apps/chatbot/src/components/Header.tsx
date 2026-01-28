/**
 * Header component for Frag die Leitlinie.
 * Left-aligned branding with action buttons on right.
 */

import React, { useState } from 'react';
import { BookOpen, Sun, Moon, Info } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { AboutModal } from './common/AboutModal';

interface HeaderProps {
  hiddenOnMobile?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ hiddenOnMobile = false }) => {
  const { theme, toggleTheme } = useTheme();
  const [aboutOpen, setAboutOpen] = useState(false);

  return (
    <>
      <header className={`sticky top-0 z-50 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-700 ${hiddenOnMobile ? 'hidden md:block' : ''}`}>
        <div className="px-3 md:px-4">
          <div className="flex items-center justify-between h-12 md:h-16">
            {/* Left: Logo and title */}
            <div className="flex items-center space-x-2 md:space-x-3">
              <div className="bg-gradient-to-br from-brand-500 to-accent-500 p-2 md:p-2.5 rounded-lg md:rounded-xl shadow-soft">
                <BookOpen className="w-5 h-5 md:w-6 md:h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg md:text-xl font-bold text-neutral-900 dark:text-neutral-50">
                  Frag die Leitlinie
                </h1>
                <p className="hidden md:block text-sm text-neutral-500 dark:text-neutral-400">
                  AWMF-Leitlinien verstehen
                </p>
              </div>
            </div>

            {/* Right: Action buttons */}
            <div className="flex items-center gap-0.5 md:gap-1">
              {/* Info button */}
              <button
                onClick={() => setAboutOpen(true)}
                className="p-2 md:p-2.5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
                title="Uber diese Seite"
                aria-label="Informationen anzeigen"
              >
                <Info className="w-4 h-4 md:w-5 md:h-5" />
              </button>

              {/* Theme toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 md:p-2.5 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
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
        </div>
      </header>

      {/* About Modal */}
      <AboutModal isOpen={aboutOpen} onClose={() => setAboutOpen(false)} />
    </>
  );
};

export default Header;
