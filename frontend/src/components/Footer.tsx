import React from 'react';
import { Link } from 'react-router-dom';
import { Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gradient-to-r from-primary-50 via-brand-50 to-accent-50 border-t border-primary-200 mt-auto">
      <div className="container mx-auto px-3 sm:px-4 py-6 sm:py-8">
        <div className="flex flex-col items-center space-y-3 sm:space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
            <Button variant="link" asChild className="text-primary-600 hover:text-primary-800 text-xs sm:text-sm px-2">
              <Link to="/impressum">Impressum</Link>
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4" />
            <Button variant="link" asChild className="text-primary-600 hover:text-primary-800 text-xs sm:text-sm px-2">
              <Link to="/datenschutz">Datenschutzerklärung</Link>
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4" />
            <Button variant="link" asChild className="text-primary-600 hover:text-primary-800 text-xs sm:text-sm px-2">
              <Link to="/nutzungsbedingungen">Nutzungsbedingungen</Link>
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4" />
            <Button variant="link" asChild className="text-primary-400 hover:text-primary-600 text-xs px-2">
              <Link to="/login">Admin</Link>
            </Button>
          </div>

          <Separator className="w-48" />

          <div className="text-center space-y-2">
            <p className="text-xs text-primary-500">
              &copy; {new Date().getFullYear()} HealthLingo. Alle Rechte vorbehalten.
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
