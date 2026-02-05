import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Header from '../components/Header';
import Footer from '../components/Footer';

const Datenschutz: React.FC = () => {
  const { t, i18n } = useTranslation('legal');

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          <h1 className="text-3xl font-bold text-primary-900 mb-8">{t('datenschutz.pageTitle')}</h1>

          <div className="space-y-6 text-primary-700">
            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section1.title')}
              </h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section1.generalTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section1.generalText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section1.dataCollectionTitle')}
              </h3>
              <p className="mb-4">
                <strong>{t('datenschutz.section1.responsibleQuestion')}</strong>
                <br />
                {t('datenschutz.section1.responsibleText')}
              </p>

              <p className="mb-4">
                <strong>{t('datenschutz.section1.anonymousTitle')}</strong>
                <br />
                {t('datenschutz.section1.anonymousText')}
              </p>

              <p className="mb-4">
                <strong>{t('datenschutz.section1.howCollectQuestion')}</strong>
                <br />
                {t('datenschutz.section1.howCollectText')}
              </p>

              <p className="mb-4">
                <strong>{t('datenschutz.section1.purposeQuestion')}</strong>
                <br />
                {t('datenschutz.section1.purposeText')}
              </p>

              <p className="mb-4">
                <strong>{t('datenschutz.section1.rightsQuestion')}</strong>
                <br />
                {t('datenschutz.section1.rightsText')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section2.title')}
              </h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section2.privacyTitle')}</h3>
              <p className="mb-4">
                {t('datenschutz.section2.privacyText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.responsiblePartyTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section2.responsiblePartyText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section2.storageDurationTitle')}</h3>
              <p className="mb-4">
                {t('datenschutz.section2.storageDurationText')}
              </p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section2.storageItems', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <p className="mb-4">
                {t('datenschutz.section2.storageDurationNote')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.sslTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section2.sslText')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section3.title')}
              </h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section3.cookiesTitle')}</h3>
              <p className="mb-4">
                <strong>{t('datenschutz.section3.cookiesText1')}</strong> {t('datenschutz.section3.cookiesText2')}
              </p>
              <p className="mb-4">
                {t('datenschutz.section3.cookiesText3')}
              </p>
              <p className="mb-4">
                {t('datenschutz.section3.cookiesText4')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section3.serverLogsTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section3.serverLogsText')}
              </p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section3.serverLogsItems', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <p className="mb-4">
                {t('datenschutz.section3.serverLogsNote')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section3.medicalTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section3.medicalText')}
              </p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section3.medicalItems', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i} dangerouslySetInnerHTML={{ __html: item }} />
                ))}
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">{t('datenschutz.section4.title')}</h2>

              <p className="mb-4">
                {t('datenschutz.section4.intro')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section4.accessTitle')}</h3>
              <p className="mb-4">
                {t('datenschutz.section4.accessText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section4.deletionTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section4.deletionText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section4.restrictionTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section4.restrictionText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section4.portabilityTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section4.portabilityText')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section4.complaintTitle')}
              </h3>
              <p className="mb-4">
                {t('datenschutz.section4.complaintText')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section6.title')}
              </h2>
              <p className="mb-4">
                {t('datenschutz.section6.text')}{' '}
                <Link
                  to="/impressum"
                  className="text-brand-600 hover:text-brand-700 underline font-medium"
                >
                  {t('datenschutz.section6.impressumLink')}
                </Link>
                .
              </p>
              <p className="mb-4">
                <strong>{t('datenschutz.section6.responsibleLabel')}</strong>
                <br />
                {t('datenschutz.section6.responsibleText')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section7.title')}
              </h2>
              <p className="mb-4">
                {t('datenschutz.section7.text')}
              </p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section7.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i} dangerouslySetInnerHTML={{ __html: item }} />
                ))}
              </ul>
              <p className="mb-4">
                {t('datenschutz.section7.note')}
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section5.title')}
              </h2>
              <p className="mb-4">
                {t('datenschutz.section5.text')}
              </p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section5.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="pt-4 border-t border-primary-200">
              <p className="text-sm text-primary-600">
                {t('datenschutz.lastUpdated')}{' '}
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

export default Datenschutz;
