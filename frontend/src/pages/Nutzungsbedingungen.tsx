import React from 'react';
import { useTranslation } from 'react-i18next';
import Header from '../components/Header';
import Footer from '../components/Footer';

const Nutzungsbedingungen: React.FC = () => {
  const { t, i18n } = useTranslation('legal');

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          <h1 className="text-3xl font-bold text-primary-900 mb-8">{t('nutzungsbedingungen.pageTitle')}</h1>

          <div className="space-y-6 text-primary-700">
            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('nutzungsbedingungen.section1.title')}</h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section1.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section1.p2')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section2.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section2.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section2.p2')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section2.p3')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section3.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section3.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section3.p2')}
              </p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('nutzungsbedingungen.section3.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <p className="mb-4">
                {t('nutzungsbedingungen.section3.p3')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section4.title')}
              </h2>
              <p className="mb-4 font-semibold text-error-700 bg-error-50 p-4 rounded-lg">
                {t('nutzungsbedingungen.section4.warning')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section4.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section4.p2')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section4.p3')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section4.p4')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section4.p5')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section5.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section5.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section5.p2')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section5.p3')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('nutzungsbedingungen.section6.title')}</h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section6.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section6.p2')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section6.p3')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section7.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section7.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section7.p2')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('nutzungsbedingungen.section8.title')}</h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section8.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section8.p2')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section8.p3')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section9.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section9.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section9.p2')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section10.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section10.p1')}
              </p>
              <p className="mb-4">
                {t('nutzungsbedingungen.section10.p2')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('nutzungsbedingungen.section11.title')}
              </h2>
              <p className="mb-4">
                {t('nutzungsbedingungen.section11.p1')}
              </p>
            </section>

            <section className="pt-4 border-t border-primary-200">
              <p className="text-sm text-primary-600">
                {t('nutzungsbedingungen.lastUpdated')}{' '}
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

export default Nutzungsbedingungen;
