import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';

interface Definition {
  term: string;
  definition: string;
}

interface Obligation {
  title: string;
  text: string;
}

const Nutzungsbedingungen: React.FC = () => {
  const { t, i18n } = useTranslation('legal');

  const tableOfContentsItems = t('nutzungsbedingungen.tableOfContents.items', { returnObjects: true }) as string[];
  const definitions = t('nutzungsbedingungen.section2.definitions', { returnObjects: true }) as Definition[];
  const contractSteps = t('nutzungsbedingungen.section3.contractSteps', { returnObjects: true }) as string[];
  const section4Sub1Items = t('nutzungsbedingungen.section4.subsection1.items', { returnObjects: true }) as string[];
  const obligations = t('nutzungsbedingungen.section7.obligations', { returnObjects: true }) as Obligation[];
  const prohibitions = t('nutzungsbedingungen.section8.prohibitions', { returnObjects: true }) as string[];
  const section9Sub1Items = t('nutzungsbedingungen.section9.subsection1.items', { returnObjects: true }) as string[];
  const section9Sub2Items = t('nutzungsbedingungen.section9.subsection2.items', { returnObjects: true }) as string[];

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          {/* Header */}
          <h1 className="text-3xl font-bold text-primary-900 mb-2">{t('nutzungsbedingungen.pageTitle')}</h1>
          <p className="text-lg text-primary-700 mb-6">{t('nutzungsbedingungen.websiteName')}</p>

          {/* Medical Disclaimer Banner */}
          <div className="mb-8 p-4 border border-amber-300 rounded-lg bg-amber-50">
            <p className="text-amber-800 font-medium">{t('nutzungsbedingungen.medicalDisclaimer')}</p>
          </div>

          {/* Table of Contents */}
          <nav className="mb-10 pb-6 border-b border-gray-200" id="inhaltsverzeichnis">
            <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.tableOfContents.title')}</h2>
            <ol className="list-decimal list-inside space-y-1 text-primary-600 columns-1 md:columns-2">
              {tableOfContentsItems.map((item, index) => (
                <li key={index} className="break-inside-avoid">
                  <a href={`#section${index + 1}`} className="hover:text-primary-900 hover:underline">
                    {item.replace(/^§\s*\d+\s*/, '')}
                  </a>
                </li>
              ))}
            </ol>
          </nav>

          <div className="space-y-8 text-primary-700">
            {/* Section 1: Geltungsbereich */}
            <section id="section1">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section1.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section1.p1')}</p>
                <p>{t('nutzungsbedingungen.section1.p2')}</p>
                <address className="not-italic ml-4 space-y-1 my-3">
                  <p className="font-medium">{t('nutzungsbedingungen.section1.providerName')}</p>
                  <p>{t('nutzungsbedingungen.section1.providerAddress')}</p>
                  <p>{t('nutzungsbedingungen.section1.providerCity')}</p>
                  <p>{t('nutzungsbedingungen.section1.providerEmail')}</p>
                  <p>{t('nutzungsbedingungen.section1.providerPhone')}</p>
                  <p className="text-sm text-primary-600">{t('nutzungsbedingungen.section1.providerNote')}</p>
                </address>
                <p>{t('nutzungsbedingungen.section1.p3')}</p>
                <p>{t('nutzungsbedingungen.section1.p4')}</p>
                <p>{t('nutzungsbedingungen.section1.p5')}</p>
                <p>{t('nutzungsbedingungen.section1.p6')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 2: Begriffsbestimmungen */}
            <section id="section2">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section2.title')}</h2>
              <p className="mb-4">{t('nutzungsbedingungen.section2.intro')}</p>
              <div className="space-y-3">
                {definitions.map((def, index) => (
                  <p key={index}>
                    <strong>„{def.term}"</strong> {def.definition}
                  </p>
                ))}
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 3: Vertragsschluss */}
            <section id="section3">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section3.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section3.p1')}</p>
                <p>{t('nutzungsbedingungen.section3.p2')}</p>
                <ul className="list-none space-y-2 ml-4">
                  {contractSteps.map((step, index) => (
                    <li key={index}>{step}</li>
                  ))}
                </ul>
                <p>{t('nutzungsbedingungen.section3.p3')}</p>
                <p>{t('nutzungsbedingungen.section3.p4')}</p>
                <p>{t('nutzungsbedingungen.section3.p5')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 4: Leistungsbeschreibung */}
            <section id="section4">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section4.title')}</h2>

              <h3 className="text-lg font-medium text-primary-900 mt-4 mb-3">{t('nutzungsbedingungen.section4.subsection1.title')}</h3>
              <p className="mb-3">{t('nutzungsbedingungen.section4.subsection1.intro')}</p>
              <ul className="list-disc list-inside space-y-1 ml-4 mb-3">
                {section4Sub1Items.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
              <p className="text-sm text-primary-600">{t('nutzungsbedingungen.section4.subsection1.note')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection2.title')}</h3>
              <p>{t('nutzungsbedingungen.section4.subsection2.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection3.title')}</h3>
              <p className="mb-2">{t('nutzungsbedingungen.section4.subsection3.documentTypes')}</p>
              <p>{t('nutzungsbedingungen.section4.subsection3.fileFormats')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection4.title')}</h3>
              <p>{t('nutzungsbedingungen.section4.subsection4.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection5.title')}</h3>
              <p>{t('nutzungsbedingungen.section4.subsection5.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection6.title')}</h3>
              <p>{t('nutzungsbedingungen.section4.subsection6.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection7.title')}</h3>
              <p>{t('nutzungsbedingungen.section4.subsection7.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section4.subsection8.title')}</h3>
              <p>{t('nutzungsbedingungen.section4.subsection8.text')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 5: Nutzungsvoraussetzungen */}
            <section id="section5">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section5.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section5.p1')}</p>
                <p>{t('nutzungsbedingungen.section5.p2')}</p>
                <p>{t('nutzungsbedingungen.section5.p3')}</p>
                <p>{t('nutzungsbedingungen.section5.p4')}</p>
                <p>{t('nutzungsbedingungen.section5.p5')}</p>
                <p>{t('nutzungsbedingungen.section5.p6')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 6: Nutzungsrechte */}
            <section id="section6">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section6.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section6.p1')}</p>
                <p>{t('nutzungsbedingungen.section6.p2')}</p>
                <p>{t('nutzungsbedingungen.section6.p3')}</p>
                <p>{t('nutzungsbedingungen.section6.p4')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 7: Pflichten des Nutzers */}
            <section id="section7">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section7.title')}</h2>
              <p className="mb-4">{t('nutzungsbedingungen.section7.intro')}</p>
              <div className="space-y-4">
                {obligations.map((obligation, index) => (
                  <div key={index}>
                    <h4 className="font-medium text-primary-900">{obligation.title}</h4>
                    <p className="mt-1">{obligation.text}</p>
                  </div>
                ))}
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 8: Verbotene Nutzung */}
            <section id="section8">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section8.title')}</h2>
              <p className="mb-4">{t('nutzungsbedingungen.section8.intro')}</p>
              <ul className="list-disc list-inside space-y-2 ml-4 mb-4">
                {prohibitions.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
              <p className="font-medium text-primary-900">{t('nutzungsbedingungen.section8.consequence')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 9: Medizinischer Haftungsausschluss */}
            <section id="section9">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section9.title')}</h2>
              <p className="font-bold text-error-700 mb-4 p-4 border border-error-300 rounded-lg bg-error-50">
                {t('nutzungsbedingungen.section9.warning')}
              </p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section9.subsection1.title')}</h3>
              <ul className="list-disc list-inside space-y-2 ml-4">
                {section9Sub1Items.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section9.subsection2.title')}</h3>
              <ul className="list-disc list-inside space-y-2 ml-4">
                {section9Sub2Items.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section9.subsection3.title')}</h3>
              <p>{t('nutzungsbedingungen.section9.subsection3.text')}</p>

              <p className="mt-4 font-medium">{t('nutzungsbedingungen.section9.acknowledgment')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 10: Hinweis zur PII-Entfernung */}
            <section id="section10">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section10.title')}</h2>
              <p className="font-bold text-amber-700 mb-4 p-4 border border-amber-300 rounded-lg bg-amber-50">
                {t('nutzungsbedingungen.section10.warning')}
              </p>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section10.p1')}</p>
                <p>{t('nutzungsbedingungen.section10.p2')}</p>
                <p>{t('nutzungsbedingungen.section10.p3')}</p>
                <p>{t('nutzungsbedingungen.section10.p4')}</p>
                <p>{t('nutzungsbedingungen.section10.p5')}</p>
              </div>
              <p className="mt-4 font-medium text-primary-900">{t('nutzungsbedingungen.section10.recommendation')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 11: Geistiges Eigentum */}
            <section id="section11">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section11.title')}</h2>

              <h3 className="text-lg font-medium text-primary-900 mt-4 mb-3">{t('nutzungsbedingungen.section11.subsection1.title')}</h3>
              <p>{t('nutzungsbedingungen.section11.subsection1.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section11.subsection2.title')}</h3>
              <p>{t('nutzungsbedingungen.section11.subsection2.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section11.subsection3.title')}</h3>
              <p>{t('nutzungsbedingungen.section11.subsection3.text')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 12: Verfügbarkeit */}
            <section id="section12">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section12.title')}</h2>

              <h3 className="text-lg font-medium text-primary-900 mt-4 mb-3">{t('nutzungsbedingungen.section12.subsection1.title')}</h3>
              <p>{t('nutzungsbedingungen.section12.subsection1.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section12.subsection2.title')}</h3>
              <p>{t('nutzungsbedingungen.section12.subsection2.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section12.subsection3.title')}</h3>
              <p>{t('nutzungsbedingungen.section12.subsection3.text')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 13: Sachmängelgewährleistung */}
            <section id="section13">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section13.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section13.p1')}</p>
                <p>{t('nutzungsbedingungen.section13.p2')}</p>
                <p>{t('nutzungsbedingungen.section13.p3')}</p>
                <p>{t('nutzungsbedingungen.section13.p4')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 14: Haftungsbeschränkung */}
            <section id="section14">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section14.title')}</h2>

              <h3 className="text-lg font-medium text-primary-900 mt-4 mb-3">{t('nutzungsbedingungen.section14.subsection1.title')}</h3>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section14.subsection1.p1')}</p>
                <p>{t('nutzungsbedingungen.section14.subsection1.p2')}</p>
                <p>{t('nutzungsbedingungen.section14.subsection1.p3')}</p>
                <p>{t('nutzungsbedingungen.section14.subsection1.p4')}</p>
                <p>{t('nutzungsbedingungen.section14.subsection1.p5')}</p>
              </div>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section14.subsection2.title')}</h3>
              <p>{t('nutzungsbedingungen.section14.subsection2.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section14.subsection3.title')}</h3>
              <p>{t('nutzungsbedingungen.section14.subsection3.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section14.subsection4.title')}</h3>
              <p>{t('nutzungsbedingungen.section14.subsection4.text')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 15: Freistellung */}
            <section id="section15">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section15.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section15.p1')}</p>
                <p>{t('nutzungsbedingungen.section15.p2')}</p>
                <p>{t('nutzungsbedingungen.section15.p3')}</p>
                <p>{t('nutzungsbedingungen.section15.p4')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 16: Datenschutz */}
            <section id="section16">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section16.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section16.p1')}</p>
                <p>{t('nutzungsbedingungen.section16.p2')}</p>
                <p>{t('nutzungsbedingungen.section16.p3')}</p>
                <p>{t('nutzungsbedingungen.section16.p4')}</p>
                <p>{t('nutzungsbedingungen.section16.p5')}</p>
                <p>{t('nutzungsbedingungen.section16.p6')}</p>
                <p className="mt-4">
                  <Link to="/datenschutz" className="text-primary-600 hover:text-primary-900 underline font-medium">
                    {t('nutzungsbedingungen.section16.linkText')}
                  </Link>
                </p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 17: Verbraucherwiderrufsrecht */}
            <section id="section17">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section17.title')}</h2>

              <h3 className="text-lg font-medium text-primary-900 mt-4 mb-3">{t('nutzungsbedingungen.section17.subsection1.title')}</h3>
              <p className="mb-3">{t('nutzungsbedingungen.section17.subsection1.text')}</p>
              <p>{t('nutzungsbedingungen.section17.subsection1.howTo')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section17.subsection2.title')}</h3>
              <p>{t('nutzungsbedingungen.section17.subsection2.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section17.subsection3.title')}</h3>
              <p className="text-sm text-primary-600 mb-2">{t('nutzungsbedingungen.section17.subsection3.note')}</p>
              <p>{t('nutzungsbedingungen.section17.subsection3.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section17.subsection4.title')}</h3>
              <p className="mb-3 text-sm italic">{t('nutzungsbedingungen.section17.subsection4.intro')}</p>
              <div className="p-4 border border-gray-200 rounded-lg bg-gray-50">
                <p className="mb-2 font-medium">An:</p>
                <address className="not-italic mb-4">
                  <p>{t('nutzungsbedingungen.section24.name')}</p>
                  <p>{t('nutzungsbedingungen.section24.address')}</p>
                  <p>{t('nutzungsbedingungen.section24.city')}, {t('nutzungsbedingungen.section24.country')}</p>
                  <p>{t('nutzungsbedingungen.section24.email')}</p>
                </address>
                <p className="whitespace-pre-line text-sm">{t('nutzungsbedingungen.section17.subsection4.formText')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 18: Vertragsbeendigung */}
            <section id="section18">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section18.title')}</h2>

              <h3 className="text-lg font-medium text-primary-900 mt-4 mb-3">{t('nutzungsbedingungen.section18.subsection1.title')}</h3>
              <p>{t('nutzungsbedingungen.section18.subsection1.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section18.subsection2.title')}</h3>
              <p>{t('nutzungsbedingungen.section18.subsection2.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section18.subsection3.title')}</h3>
              <p>{t('nutzungsbedingungen.section18.subsection3.text')}</p>

              <h3 className="text-lg font-medium text-primary-900 mt-6 mb-3">{t('nutzungsbedingungen.section18.subsection4.title')}</h3>
              <p>{t('nutzungsbedingungen.section18.subsection4.text')}</p>
            </section>

            <hr className="border-gray-200" />

            {/* Section 19: Änderungen */}
            <section id="section19">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section19.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section19.p1')}</p>
                <p>{t('nutzungsbedingungen.section19.p2')}</p>
                <p>{t('nutzungsbedingungen.section19.p3')}</p>
                <p>{t('nutzungsbedingungen.section19.p4')}</p>
                <p>{t('nutzungsbedingungen.section19.p5')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 20: Anwendbares Recht */}
            <section id="section20">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section20.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section20.p1')}</p>
                <p>{t('nutzungsbedingungen.section20.p2')}</p>
                <p>{t('nutzungsbedingungen.section20.p3')}</p>
                <p>{t('nutzungsbedingungen.section20.p4')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 21: Außergerichtliche Streitbeilegung */}
            <section id="section21">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section21.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section21.p1')}</p>
                <p>{t('nutzungsbedingungen.section21.p2')}</p>
                <p>{t('nutzungsbedingungen.section21.p3')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 22: Aufrechnung und Zurückbehaltung */}
            <section id="section22">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section22.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section22.p1')}</p>
                <p>{t('nutzungsbedingungen.section22.p2')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 23: Salvatorische Klausel */}
            <section id="section23">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section23.title')}</h2>
              <div className="space-y-3">
                <p>{t('nutzungsbedingungen.section23.p1')}</p>
                <p>{t('nutzungsbedingungen.section23.p2')}</p>
                <p>{t('nutzungsbedingungen.section23.p3')}</p>
                <p>{t('nutzungsbedingungen.section23.p4')}</p>
              </div>
            </section>

            <hr className="border-gray-200" />

            {/* Section 24: Kontakt */}
            <section id="section24">
              <h2 className="text-xl font-semibold text-primary-900 mb-4">{t('nutzungsbedingungen.section24.title')}</h2>
              <p className="mb-4">{t('nutzungsbedingungen.section24.intro')}</p>
              <address className="not-italic space-y-1">
                <p className="font-medium">{t('nutzungsbedingungen.section24.name')}</p>
                <p>{t('nutzungsbedingungen.section24.address')}</p>
                <p>{t('nutzungsbedingungen.section24.city')}</p>
                <p>{t('nutzungsbedingungen.section24.country')}</p>
                <p className="mt-2">{t('nutzungsbedingungen.section24.email')}</p>
                <p>{t('nutzungsbedingungen.section24.phone')}</p>
              </address>
            </section>

            {/* Last Updated */}
            <section className="pt-6 border-t border-primary-200">
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
