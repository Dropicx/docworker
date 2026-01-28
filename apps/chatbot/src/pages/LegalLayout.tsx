/**
 * Shared layout for legal pages (Impressum, Datenschutz, Nutzungsbedingungen).
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

interface LegalLayoutProps {
  title: string;
  children: React.ReactNode;
}

export const LegalLayout: React.FC<LegalLayoutProps> = ({ title, children }) => {
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Header */}
      <header className="bg-white border-b border-neutral-200">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link
            to="/"
            className="flex items-center gap-2 text-brand-600 hover:text-brand-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Zuruck zum Chat</span>
          </Link>
          <div className="flex items-center gap-2">
            <img
              src="/logo.svg"
              alt="Frag die Leitlinie"
              className="h-8 w-auto"
            />
            <span className="font-semibold text-neutral-800">Frag die Leitlinie</span>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-neutral-200 p-6 md:p-8">
          <h1 className="text-2xl md:text-3xl font-bold text-neutral-800 mb-6">
            {title}
          </h1>
          <div className="prose prose-neutral max-w-none">
            {children}
          </div>
        </div>

        {/* Footer links */}
        <div className="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-2">
          <Link to="/impressum" className="text-sm text-neutral-500 hover:text-neutral-700">
            Impressum
          </Link>
          <Link to="/datenschutz" className="text-sm text-neutral-500 hover:text-neutral-700">
            Datenschutz
          </Link>
          <Link to="/nutzungsbedingungen" className="text-sm text-neutral-500 hover:text-neutral-700">
            Nutzungsbedingungen
          </Link>
        </div>
      </main>
    </div>
  );
};

export default LegalLayout;
