/**
 * About modal with service description and disclaimers.
 */

import React, { useEffect } from 'react';
import { X, BookOpen, AlertCircle, Shield } from 'lucide-react';

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AboutModal: React.FC<AboutModalProps> = ({ isOpen, onClose }) => {
  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-lg transform rounded-2xl bg-white dark:bg-neutral-800 shadow-xl transition-all animate-slide-up">
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute right-4 top-4 p-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="p-6">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-gradient-to-br from-brand-500 to-accent-500 rounded-xl flex items-center justify-center shadow-soft">
                <BookOpen className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-neutral-900 dark:text-neutral-50">
                  Uber Frag die Leitlinie
                </h2>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  AWMF-Leitlinien verstehen
                </p>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-4 mb-6">
              <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
                Dieser KI-Assistent hilft Ihnen, deutsche medizinische Leitlinien (AWMF)
                besser zu verstehen. Stellen Sie Fragen zu Diagnosen, Behandlungen oder
                medizinischen Empfehlungen - der Assistent durchsucht die Leitlinien-Datenbank
                und liefert fundierte Antworten mit Quellenangaben.
              </p>
            </div>

            {/* Disclaimers */}
            <div className="space-y-3">
              {/* Medical disclaimer */}
              <div className="flex gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
                <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                    Kein Ersatz fur arztliche Beratung
                  </p>
                  <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                    Die bereitgestellten Informationen ersetzen nicht die professionelle
                    medizinische Beratung, Diagnose oder Behandlung durch qualifiziertes
                    medizinisches Fachpersonal.
                  </p>
                </div>
              </div>

              {/* Data disclaimer */}
              <div className="flex gap-3 p-3 bg-neutral-50 dark:bg-neutral-700/50 border border-neutral-200 dark:border-neutral-600 rounded-xl">
                <Shield className="w-5 h-5 text-neutral-600 dark:text-neutral-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                    Datenschutz
                  </p>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">
                    Ihre Chatverlaufe werden lokal in Ihrem Browser gespeichert.
                    Es werden keine personenbezogenen Daten an Dritte weitergegeben.
                  </p>
                </div>
              </div>
            </div>

            {/* Close button */}
            <button
              onClick={onClose}
              className="w-full mt-6 py-2.5 px-4 bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-200 font-medium rounded-xl hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors"
            >
              Verstanden
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutModal;
