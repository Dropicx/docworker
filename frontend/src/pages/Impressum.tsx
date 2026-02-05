import React from 'react';
import { useTranslation } from 'react-i18next';
import Header from '../components/Header';
import Footer from '../components/Footer';

const Impressum: React.FC = () => {
  const { t, i18n } = useTranslation('legal');

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          <h1 className="text-3xl font-bold text-primary-900 mb-8">{t('impressum.pageTitle')}</h1>

          <div className="space-y-6 text-primary-700">
            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('impressum.section1.title')}</h2>
              <p className="mb-2">{t('impressum.section1.name')}</p>
              <p className="mb-2">{t('impressum.section1.address')}</p>
              <p className="mb-2">{t('impressum.section1.city')}</p>
              <p>{t('impressum.section1.country')}</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('impressum.contact.title')}</h2>
              <p className="mb-2">{t('impressum.contact.phoneLabel')} {t('impressum.contact.phone')}</p>
              <p className="mb-2">{t('impressum.contact.emailLabel')} {t('impressum.contact.email')}</p>
              <p>{t('impressum.contact.websiteLabel')} {t('impressum.contact.website')}</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('impressum.register.title')}</h2>
              <p className="mb-2">{t('impressum.register.entry')}</p>
              <p className="mb-2">{t('impressum.register.courtLabel')} {t('impressum.register.court')}</p>
              <p>{t('impressum.register.numberLabel')} {t('impressum.register.number')}</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('impressum.vat.title')}</h2>
              <p>{t('impressum.vat.text')}</p>
              <p>{t('impressum.vat.number')}</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('impressum.profession.title')}
              </h2>
              <p className="mb-2">{t('impressum.profession.titleLabel')} {t('impressum.profession.name')}</p>
              <p className="mb-2">{t('impressum.profession.chamberLabel')} {t('impressum.profession.chamber')}</p>
              <p className="mb-2">{t('impressum.profession.grantedLabel')} {t('impressum.profession.granted')}</p>
              <p>{t('impressum.profession.rulesText')} {t('impressum.profession.rules')}</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('impressum.responsible.title')}
              </h2>
              <p className="mb-2">{t('impressum.responsible.name')}</p>
              <p className="mb-2">{t('impressum.responsible.address')}</p>
              <p>{t('impressum.responsible.city')}</p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('impressum.disclaimer.title')}</h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('impressum.disclaimer.contentTitle')}
              </h3>
              <p className="mb-4">
                {t('impressum.disclaimer.contentText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('impressum.disclaimer.linksTitle')}
              </h3>
              <p className="mb-4">
                {t('impressum.disclaimer.linksText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('impressum.disclaimer.copyrightTitle')}</h3>
              <p>
                {t('impressum.disclaimer.copyrightText')}
              </p>
            </section>

            <section className="pt-4 border-t border-primary-200">
              <p className="text-sm text-primary-600">
                {t('impressum.lastUpdated')}{' '}
                {new Date().toLocaleDateString(i18n.language === 'de' ? 'de-DE' : 'en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </section>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Impressum;
