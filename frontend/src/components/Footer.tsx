import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Heart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

const Footer: React.FC = () => {
  const { t } = useTranslation();

  return (
    <footer className="bg-gradient-to-r from-primary-50 via-brand-50 to-accent-50 border-t border-primary-200 mt-auto">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8">
        <div className="flex flex-col items-center space-y-3 sm:space-y-4">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2">
            <Button
              variant="link"
              asChild
              className="text-primary-600 hover:text-primary-800 text-xs sm:text-sm px-2"
            >
              <Link to="/impressum">{t('footer.impressum')}</Link>
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4 bg-primary-300" />
            <Button
              variant="link"
              asChild
              className="text-primary-600 hover:text-primary-800 text-xs sm:text-sm px-2"
            >
              <Link to="/datenschutz">{t('footer.privacy')}</Link>
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4 bg-primary-300" />
            <Button
              variant="link"
              asChild
              className="text-primary-600 hover:text-primary-800 text-xs sm:text-sm px-2"
            >
              <Link to="/nutzungsbedingungen">{t('footer.terms')}</Link>
            </Button>
            <Separator orientation="vertical" className="hidden sm:block h-4 bg-primary-300" />
            <Button
              variant="link"
              asChild
              className="text-primary-400 hover:text-primary-600 text-xs px-2"
            >
              <Link to="/login">{t('footer.admin')}</Link>
            </Button>
          </div>

          <Separator className="w-48 bg-primary-200" />

          <div className="text-center space-y-2">
            <p className="text-xs text-primary-500">
              &copy; {new Date().getFullYear()} {t('footer.copyright')}
            </p>
            <p className="text-xs text-primary-400 flex items-center justify-center gap-1">
              {t('footer.madeWith')} <Heart className="w-3 h-3 text-red-500 fill-current" /> {t('footer.madeInLocation')}
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
