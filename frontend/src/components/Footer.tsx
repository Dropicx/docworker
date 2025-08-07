import React from 'react';
import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gradient-to-r from-primary-50 via-brand-50 to-accent-50 border-t border-primary-200 mt-auto">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col items-center space-y-4">
          <div className="flex flex-wrap justify-center gap-6 text-sm">
            <Link 
              to="/impressum" 
              className="text-primary-600 hover:text-primary-800 transition-colors font-medium"
            >
              Impressum
            </Link>
            <span className="text-primary-300">|</span>
            <Link 
              to="/datenschutz" 
              className="text-primary-600 hover:text-primary-800 transition-colors font-medium"
            >
              Datenschutzerklärung
            </Link>
            <span className="text-primary-300">|</span>
            <Link 
              to="/nutzungsbedingungen" 
              className="text-primary-600 hover:text-primary-800 transition-colors font-medium"
            >
              Nutzungsbedingungen
            </Link>
          </div>
          
          <div className="text-center space-y-2">
            <p className="text-xs text-primary-500">
              © {new Date().getFullYear()} HealthLingo. Alle Rechte vorbehalten.
            </p>
            <p className="text-xs text-primary-400 flex items-center justify-center gap-1">
              Mit <Heart className="w-3 h-3 text-red-500 fill-current" /> in Deutschland entwickelt
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;