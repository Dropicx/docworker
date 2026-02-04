import React from 'react';
import Header from '../components/Header';
import Footer from '../components/Footer';

const Impressum: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          <h1 className="text-3xl font-bold text-primary-900 mb-8">Impressum</h1>

          <div className="space-y-6 text-primary-700">
              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  Angaben gemäß § 5 TMG
                </h2>
                <p className="mb-2">[Ihr Name oder Firmenname]</p>
                <p className="mb-2">[Ihre Adresse]</p>
                <p className="mb-2">[PLZ und Ort]</p>
                <p>Deutschland</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">Kontakt</h2>
                <p className="mb-2">Telefon: [Ihre Telefonnummer]</p>
                <p className="mb-2">E-Mail: [Ihre E-Mail-Adresse]</p>
                <p>Website: [Ihre Website-URL]</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">Registereintrag</h2>
                <p className="mb-2">Eintragung im Handelsregister.</p>
                <p className="mb-2">Registergericht: [Ihr Registergericht]</p>
                <p>Registernummer: [Ihre Registernummer]</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">Umsatzsteuer-ID</h2>
                <p>Umsatzsteuer-Identifikationsnummer gemäß § 27 a Umsatzsteuergesetz:</p>
                <p>[Ihre USt-IdNr.]</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  Berufsbezeichnung und berufsrechtliche Regelungen
                </h2>
                <p className="mb-2">Berufsbezeichnung: [Ihre Berufsbezeichnung]</p>
                <p className="mb-2">Zuständige Kammer: [Ihre zuständige Kammer]</p>
                <p className="mb-2">Verliehen in: Deutschland</p>
                <p>Es gelten folgende berufsrechtliche Regelungen: [Relevante Regelungen]</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV
                </h2>
                <p className="mb-2">[Name des Verantwortlichen]</p>
                <p className="mb-2">[Adresse]</p>
                <p>[PLZ und Ort]</p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">Haftungsausschluss</h2>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Haftung für Inhalte
                </h3>
                <p className="mb-4">
                  Die Inhalte unserer Seiten wurden mit größter Sorgfalt erstellt. Für die
                  Richtigkeit, Vollständigkeit und Aktualität der Inhalte können wir jedoch keine
                  Gewähr übernehmen. Als Diensteanbieter sind wir gemäß § 7 Abs.1 TMG für eigene
                  Inhalte auf diesen Seiten nach den allgemeinen Gesetzen verantwortlich.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Haftung für Links
                </h3>
                <p className="mb-4">
                  Unser Angebot enthält Links zu externen Webseiten Dritter, auf deren Inhalte wir
                  keinen Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine
                  Gewähr übernehmen. Für die Inhalte der verlinkten Seiten ist stets der jeweilige
                  Anbieter oder Betreiber der Seiten verantwortlich.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Urheberrecht</h3>
                <p>
                  Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten
                  unterliegen dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung,
                  Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechtes
                  bedürfen der schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.
                </p>
              </section>

            <section className="pt-4 border-t border-primary-200">
              <p className="text-sm text-primary-600">
                Stand:{' '}
                {new Date().toLocaleDateString('de-DE', {
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
