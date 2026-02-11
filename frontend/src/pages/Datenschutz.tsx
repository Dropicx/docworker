import React from 'react';
import { useTranslation } from 'react-i18next';
import Header from '../components/Header';
import Footer from '../components/Footer';

interface MedicalItem {
  title: string;
  text: string;
}

interface LegalBasis {
  activity: string;
  basis: string;
  explanation: string;
}

interface Definition {
  term: string;
  article: string;
  definition: string;
}

const Datenschutz: React.FC = () => {
  const { t, i18n } = useTranslation('legal');

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          <h1 className="text-3xl font-bold text-primary-900 mb-2">{t('datenschutz.pageTitle')}</h1>
          <p className="text-lg text-primary-600 mb-6">{t('datenschutz.websiteName')}</p>

          {/* Table of Contents */}
          <nav className="mb-8 pb-6 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-primary-900 mb-3 uppercase tracking-wide">{t('datenschutz.tableOfContents.title')}</h2>
            <ol className="grid grid-cols-1 md:grid-cols-2 gap-1 text-sm">
              {(t('datenschutz.tableOfContents.items', { returnObjects: true }) as string[]).map((item, i) => (
                <li key={i}>
                  <a href={`#section${i + 1}`} className="text-primary-600 hover:text-primary-900 hover:underline">
                    {item}
                  </a>
                </li>
              ))}
            </ol>
          </nav>

          <div className="space-y-8 text-primary-700">
            {/* Section 1: Datenschutz auf einen Blick */}
            <section id="section1">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section1.title')}
              </h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section1.generalTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section1.generalText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section1.responsibleQuestion')}
              </h3>
              <p className="mb-2">{t('datenschutz.section1.responsibleIntro')}</p>
              <div className="mb-4 ml-4">
                <p className="font-semibold">{t('datenschutz.section1.responsibleName')}</p>
                <p>{t('datenschutz.section1.responsibleAddress')}</p>
                <p>{t('datenschutz.section1.responsibleCity')}</p>
                <p>{t('datenschutz.section1.responsibleEmail')}</p>
                <p>{t('datenschutz.section1.responsiblePhone')}</p>
              </div>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section1.dpoTitle')}
              </h3>
              <p className="mb-4 text-sm italic">{t('datenschutz.section1.dpoText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section1.serviceTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section1.serviceText')}</p>

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

            <hr className="border-gray-200" />

            {/* Section 2: Allgemeine Hinweise und Pflichtinformationen */}
            <section id="section2">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section2.title')}
              </h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.privacyTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section2.privacyText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.responsibleTitle')}
              </h3>
              <p className="mb-2">{t('datenschutz.section2.responsibleIntro')}</p>
              <div className="mb-4 ml-4">
                <p className="font-semibold">{t('datenschutz.section2.responsibleName')}</p>
                <p>{t('datenschutz.section2.responsibleAddress')}</p>
                <p>{t('datenschutz.section2.responsibleCity')}</p>
                <p>{t('datenschutz.section2.responsibleEmail')}</p>
                <p>{t('datenschutz.section2.responsiblePhone')}</p>
              </div>
              <p className="mb-4 text-sm">{t('datenschutz.section2.responsibleNote')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.supervisoryTitle')}
              </h3>
              <div className="mb-4 ml-4">
                <p className="font-semibold">{t('datenschutz.section2.supervisoryName')}</p>
                <p>{t('datenschutz.section2.supervisoryAddress')}</p>
                <p>{t('datenschutz.section2.supervisoryEmail')}</p>
                <p>{t('datenschutz.section2.supervisoryPhone')}</p>
              </div>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.definitionsTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section2.definitionsIntro')}</p>
              <div className="space-y-2 mb-4 ml-4">
                {(t('datenschutz.section2.definitions', { returnObjects: true }) as Definition[]).map((def, i) => (
                  <p key={i}>
                    <strong>„{def.term}"</strong> ({def.article}) {def.definition}
                  </p>
                ))}
              </div>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.storageTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section2.storageText')}</p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section2.storageItems', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <p className="mb-4">{t('datenschutz.section2.storageNote')}</p>

              <h4 className="font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.storageRetainedTitle')}
              </h4>
              <p className="mb-4">{t('datenschutz.section2.storageRetainedText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.voluntaryTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section2.voluntaryText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section2.sslTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section2.sslText')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 3: Datenerfassung auf dieser Website */}
            <section id="section3">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section3.title')}
              </h2>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section3.cookiesTitle')}
              </h3>
              <p className="mb-4"><strong>{t('datenschutz.section3.cookiesText')}</strong></p>
              <p className="mb-4">{t('datenschutz.section3.cookiesLocalStorage')}</p>
              <p className="mb-4">{t('datenschutz.section3.cookiesConsentNote')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section3.serverLogsTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section3.serverLogsText')}</p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section3.serverLogsItems', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <p className="mb-4">{t('datenschutz.section3.serverLogsNote')}</p>
              <p className="mb-4">
                <strong>{t('datenschutz.labels.objectionRight')}</strong> {t('datenschutz.section3.serverLogsObjection')}
              </p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                {t('datenschutz.section3.medicalTitle')}
              </h3>
              <p className="mb-4">{t('datenschutz.section3.medicalText')}</p>
              <ul className="list-disc list-inside mb-4 ml-4 space-y-2">
                {(t('datenschutz.section3.medicalItems', { returnObjects: true }) as MedicalItem[]).map((item, i) => (
                  <li key={i}><strong>{item.title}:</strong> {item.text}</li>
                ))}
              </ul>
            </section>

            <hr className="border-gray-200" />

            {/* Section 4: Rechtsgrundlagen der Verarbeitung */}
            <section id="section4">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section4.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section4.intro')}</p>
              <div className="overflow-x-auto">
                <table className="min-w-full border border-gray-300 mb-4">
                  <thead>
                    <tr className="border-b border-gray-300">
                      <th className="px-4 py-2 text-left text-sm font-semibold text-primary-900">{t('datenschutz.labels.processingActivity')}</th>
                      <th className="px-4 py-2 text-left text-sm font-semibold text-primary-900">{t('datenschutz.labels.legalBasis').replace(':', '')}</th>
                      <th className="px-4 py-2 text-left text-sm font-semibold text-primary-900">{t('datenschutz.labels.explanation')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(t('datenschutz.section4.legalBases', { returnObjects: true }) as LegalBasis[]).map((basis, i) => (
                      <tr key={i} className="border-b border-gray-200">
                        <td className="px-4 py-2 text-sm">{basis.activity}</td>
                        <td className="px-4 py-2 text-sm font-medium">{basis.basis}</td>
                        <td className="px-4 py-2 text-sm">{basis.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 5: Besondere Hinweise zum Gesundheitsdatenschutz */}
            <section id="section5">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section5.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section5.intro')}</p>
              <ul className="list-disc list-inside mb-4 ml-4 space-y-2">
                {(t('datenschutz.section5.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </section>

            <hr className="border-gray-200" />

            {/* Section 6: Drittparteien und Datenverarbeitung */}
            <section id="section6">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section6.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section6.intro')}</p>

              {/* Cloudflare */}
              <div className="mb-6">
                <h4 className="font-semibold text-primary-900 mb-1">{t('datenschutz.section6.cloudflare.title')}</h4>
                <p className="text-sm text-primary-600 mb-2">{t('datenschutz.section6.cloudflare.address')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.purpose')}</strong> {t('datenschutz.section6.cloudflare.purpose')}</p>
                <p className="mb-2">{t('datenschutz.section6.cloudflare.importance')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.dataProcessed')}</strong> {t('datenschutz.section6.cloudflare.dataProcessed')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.security')}</strong> {t('datenschutz.section6.cloudflare.security')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.legalBasis')}</strong> {t('datenschutz.section6.cloudflare.legalBasis')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.thirdCountryTransfer')}</strong> {t('datenschutz.section6.cloudflare.thirdCountryTransfer')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.retention')}</strong> {t('datenschutz.section6.cloudflare.retention')}</p>
                <p className="text-sm">{t('datenschutz.section6.cloudflare.dpaNote')}</p>
              </div>

              {/* Mistral AI */}
              <div className="mb-6">
                <h4 className="font-semibold text-primary-900 mb-1">{t('datenschutz.section6.mistral.title')}</h4>
                <p className="text-sm text-primary-600 mb-2">{t('datenschutz.section6.mistral.address')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.purpose')}</strong> {t('datenschutz.section6.mistral.purpose')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.ocrNote')}</strong> {t('datenschutz.section6.mistral.ocrNote')}</p>
                <p className="text-sm">{t('datenschutz.section6.mistral.legalBasis')}</p>
              </div>

              {/* Hetzner */}
              <div className="mb-6">
                <h4 className="font-semibold text-primary-900 mb-1">{t('datenschutz.section6.hetzner.title')}</h4>
                <p className="text-sm text-primary-600 mb-2">{t('datenschutz.section6.hetzner.address')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.purpose')}</strong> {t('datenschutz.section6.hetzner.purpose')}</p>
                <p className="text-sm">{t('datenschutz.section6.hetzner.legalBasis')}</p>
              </div>

              {/* Railway */}
              <div className="mb-6">
                <h4 className="font-semibold text-primary-900 mb-1">{t('datenschutz.section6.railway.title')}</h4>
                <p className="text-sm text-primary-600 mb-2">{t('datenschutz.section6.railway.address')}</p>
                <p className="mb-2"><strong>{t('datenschutz.labels.purpose')}</strong> {t('datenschutz.section6.railway.purpose')}</p>
                <p className="mb-2">{t('datenschutz.section6.railway.legalBasis')}</p>
                <p className="text-sm italic">{t('datenschutz.section6.railway.thirdCountryNote')}</p>
              </div>

              <p className="mb-4">{t('datenschutz.section6.dpaNote')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 7: Wichtiger Hinweis zur PII-Entfernung */}
            <section id="section7">
              <h2 className="text-xl font-semibold text-primary-900 mb-3">
                {t('datenschutz.section7.title')}
              </h2>
              <p className="mb-4 font-semibold">
                ⚠️ {t('datenschutz.section7.warning')}
              </p>
              <p className="mb-4">{t('datenschutz.section7.warningText')}</p>
              <p className="mb-4">{t('datenschutz.section7.limitationsText')}</p>
              <p className="mb-4"><strong>{t('datenschutz.labels.important')}</strong> {t('datenschutz.section7.ocrWarning')}</p>
              <p className="mb-4">{t('datenschutz.section7.recommendation')}</p>
              <p className="mb-4">{t('datenschutz.section7.medicalTermsNote')}</p>
              <p className="text-sm italic">{t('datenschutz.section7.consent')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 8: Automatisierte Verarbeitung und KI */}
            <section id="section8">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section8.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section8.intro')}</p>
              <ul className="list-disc list-inside mb-4 ml-4 space-y-2">
                {(t('datenschutz.section8.items', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </section>

            <hr className="border-gray-200" />

            {/* Section 9: Ihre Einwilligung */}
            <section id="section9">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section9.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section9.intro')}</p>
              <p className="mb-4 font-semibold">{t('datenschutz.section9.consentRequest')}</p>

              {/* Consent 1 */}
              <div className="mb-6 ml-4">
                <h4 className="font-semibold text-primary-900 mb-2">{t('datenschutz.section9.consent1.title')}</h4>
                <p className="mb-2">{t('datenschutz.section9.consent1.text')}</p>
                <ul className="list-disc list-inside mb-4 ml-4 space-y-1">
                  {(t('datenschutz.section9.consent1.points', { returnObjects: true }) as string[]).map((point, i) => (
                    <li key={i}>{point}</li>
                  ))}
                </ul>
                <p className="font-medium">☐ {t('datenschutz.section9.consent1.checkbox')}</p>
              </div>

              {/* Consent 2 */}
              <div className="mb-6 ml-4">
                <h4 className="font-semibold text-primary-900 mb-2">{t('datenschutz.section9.consent2.title')}</h4>
                <p className="mb-2">{t('datenschutz.section9.consent2.text')}</p>
                <p className="font-medium">☐ {t('datenschutz.section9.consent2.checkbox')}</p>
              </div>

              <p className="mb-4 text-sm">{t('datenschutz.section9.consentNote')}</p>

              <h4 className="font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section9.withdrawalTitle')}</h4>
              <p className="mb-2">{t('datenschutz.section9.withdrawalText')}</p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section9.withdrawalMethods', { returnObjects: true }) as string[]).map((method, i) => (
                  <li key={i}>{method}</li>
                ))}
              </ul>
              <p className="mb-4">{t('datenschutz.section9.withdrawalNote')}</p>
              <p className="text-sm">{t('datenschutz.section9.withdrawalConsequence')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 10: Ihre Rechte */}
            <section id="section10">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section10.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section10.intro')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.accessTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.accessText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.rectificationTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.rectificationText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.deletionTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.deletionText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.restrictionTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.restrictionText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.portabilityTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.portabilityText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.objectionTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.objectionText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.withdrawalTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.withdrawalText')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section10.complaintTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section10.complaintText')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 11: Feedback und Nutzerbewertungen */}
            <section id="section11">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section11.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section11.intro')}</p>
              <ul className="list-disc list-inside mb-4 ml-4">
                {(t('datenschutz.section11.dataCollected', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
              <p className="mb-4">{t('datenschutz.section11.consentNote')}</p>

              <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">{t('datenschutz.section11.retentionTitle')}</h3>
              <p className="mb-4">{t('datenschutz.section11.retentionText')}</p>

              <p className="mb-4 text-sm">
                <strong>{t('datenschutz.labels.note')}</strong> {t('datenschutz.section11.warning')}
              </p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 12: Datensicherheit */}
            <section id="section12">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section12.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section12.intro')}</p>
              <ul className="list-disc list-inside mb-4 ml-4 space-y-2">
                {(t('datenschutz.section12.measures', { returnObjects: true }) as string[]).map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </section>

            <hr className="border-gray-200" />

            {/* Section 13: Kontakt und Datenschutzanfragen */}
            <section id="section13">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section13.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section13.text')}</p>
              <div className="mb-4 ml-4">
                <p className="font-semibold">{t('datenschutz.section13.contactName')}</p>
                <p>{t('datenschutz.section13.contactEmail')}</p>
                <p>{t('datenschutz.section13.contactAddress')}</p>
              </div>
              <p className="mb-4">{t('datenschutz.section13.responseNote')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 14: Aktualisierung dieser Datenschutzerklärung */}
            <section id="section14">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">
                {t('datenschutz.section14.title')}
              </h2>
              <p className="mb-4">{t('datenschutz.section14.text')}</p>
              <p className="mb-4 text-sm">{t('datenschutz.section14.versionNote')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Last Updated */}
            <section>
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
