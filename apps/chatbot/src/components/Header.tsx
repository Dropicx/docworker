/**
 * Simplified header for Frag die Leitlinie standalone app.
 * Branding only - no navigation or auth.
 */

import React from 'react';
import { BookOpen } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-sm border-b border-neutral-200">
      <div className="max-w-4xl mx-auto px-4">
        <div className="flex items-center h-16">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-brand-500 to-accent-500 p-2.5 rounded-xl shadow-soft">
              <BookOpen className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-neutral-900">Frag die Leitlinie</h1>
              <p className="text-sm text-neutral-500">AWMF-Leitlinien verstehen</p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
