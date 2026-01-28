/**
 * First-visit consent modal for terms and privacy.
 * Non-dismissible - user must accept to continue.
 */

import React, { useState } from 'react';
import { Shield, ExternalLink } from 'lucide-react';

interface ConsentModalProps {
  isOpen: boolean;
  onAccept: () => void;
}

export const ConsentModal: React.FC<ConsentModalProps> = ({ isOpen, onAccept }) => {
  const [checked, setChecked] = useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] overflow-y-auto">
      {/* Backdrop - no click handler */}
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-md transform rounded-2xl bg-white dark:bg-neutral-800 shadow-2xl transition-all animate-slide-up">
          <div className="p-6">
            {/* Icon and title */}
            <div className="flex flex-col items-center text-center mb-6">
              <div className="w-14 h-14 bg-brand-100 dark:bg-brand-900/30 rounded-2xl flex items-center justify-center mb-4">
                <Shield className="w-7 h-7 text-brand-600 dark:text-brand-400" />
              </div>
              <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">
                Nutzungsbedingungen & Datenschutz
              </h2>
            </div>

            {/* Description */}
            <p className="text-sm text-neutral-600 dark:text-neutral-300 text-center mb-6">
              Bevor Sie fortfahren, lesen Sie bitte unsere Nutzungsbedingungen
              und Datenschutzerklarung.
            </p>

            {/* Checkbox */}
            <label className="flex items-start gap-3 p-4 bg-neutral-50 dark:bg-neutral-700/50 rounded-xl cursor-pointer mb-6 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors">
              <input
                type="checkbox"
                checked={checked}
                onChange={e => setChecked(e.target.checked)}
                className="mt-0.5 w-5 h-5 rounded border-neutral-300 dark:border-neutral-600 text-brand-600 focus:ring-brand-500 focus:ring-offset-0 cursor-pointer"
              />
              <span className="text-sm text-neutral-700 dark:text-neutral-200 leading-relaxed">
                Ich habe die Nutzungsbedingungen und Datenschutzerklarung gelesen und akzeptiere diese.
              </span>
            </label>

            {/* Links */}
            <div className="flex justify-center gap-4 mb-6">
              <a
                href="/nutzungsbedingungen"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium transition-colors"
              >
                Nutzungsbedingungen
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <a
                href="/datenschutz"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium transition-colors"
              >
                Datenschutz
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* Accept button */}
            <button
              onClick={onAccept}
              disabled={!checked}
              className="w-full py-3 px-4 bg-brand-600 text-white font-medium rounded-xl hover:bg-brand-700 disabled:bg-neutral-200 dark:disabled:bg-neutral-700 disabled:text-neutral-400 dark:disabled:text-neutral-500 disabled:cursor-not-allowed transition-colors"
            >
              Fortfahren
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConsentModal;
