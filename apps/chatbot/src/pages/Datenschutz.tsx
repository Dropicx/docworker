/**
 * Datenschutz (Privacy Policy) page - Required by GDPR.
 */

import React from 'react';
import { LegalLayout } from './LegalLayout';

export const Datenschutz: React.FC = () => {
  return (
    <LegalLayout title="Datenschutzerklarung">
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          1. Verantwortlicher
        </h2>
        <p className="text-neutral-600 mb-4">
          Verantwortlich fur die Datenverarbeitung auf dieser Website ist:
        </p>
        <address className="not-italic text-neutral-600 leading-relaxed">
          HealthLingo UG (haftungsbeschrankt)<br />
          Musterstrasse 123<br />
          10115 Berlin<br />
          Deutschland<br />
          E-Mail: <a href="mailto:datenschutz@fragdieleitlinie.de" className="text-brand-600 hover:underline">datenschutz@fragdieleitlinie.de</a>
        </address>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          2. Erhobene Daten
        </h2>
        <p className="text-neutral-600 mb-4">
          Bei der Nutzung von "Frag die Leitlinie" werden folgende Daten verarbeitet:
        </p>
        <ul className="list-disc list-inside text-neutral-600 space-y-2">
          <li>
            <strong>Chatveraufe:</strong> Ihre Unterhaltungen werden ausschliesslich lokal
            in Ihrem Browser (localStorage) gespeichert. Wir haben keinen Zugriff auf diese Daten.
          </li>
          <li>
            <strong>Chatnachrichten:</strong> Zur Beantwortung Ihrer Fragen werden Ihre
            Nachrichten an unseren Backend-Server ubertragen und dort von einer KI verarbeitet.
            Diese Nachrichten werden nicht dauerhaft gespeichert.
          </li>
          <li>
            <strong>Technische Daten:</strong> Bei jedem Zugriff auf unsere Website werden
            automatisch technische Informationen erfasst (IP-Adresse, Browsertyp, Zugriffszeit).
            Diese Daten werden fur den technischen Betrieb benotigt und nach kurzer Zeit geloscht.
          </li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          3. Cookies
        </h2>
        <p className="text-neutral-600">
          Diese Website verwendet keine Tracking-Cookies. Wir setzen lediglich technisch
          notwendige Cookies ein, die fur den Betrieb der Website erforderlich sind.
          Ihre Chatveraufe werden in localStorage gespeichert, nicht in Cookies.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          4. Datenverarbeitung und KI
        </h2>
        <p className="text-neutral-600 mb-4">
          Wenn Sie eine Frage stellen, wird diese an unsere Server ubertragen und von einem
          KI-System (Large Language Model) verarbeitet. Die Verarbeitung erfolgt auf Servern
          in der Europaischen Union. Ihre Fragen werden:
        </p>
        <ul className="list-disc list-inside text-neutral-600 space-y-2">
          <li>Nicht fur das Training von KI-Modellen verwendet</li>
          <li>Nicht dauerhaft gespeichert</li>
          <li>Anonymisiert fur Qualitatsverbesserungen ausgewertet</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          5. Ihre Rechte (DSGVO)
        </h2>
        <p className="text-neutral-600 mb-4">
          Nach der Datenschutz-Grundverordnung stehen Ihnen folgende Rechte zu:
        </p>
        <ul className="list-disc list-inside text-neutral-600 space-y-2">
          <li><strong>Auskunftsrecht:</strong> Sie konnen Auskunft uber Ihre gespeicherten Daten verlangen.</li>
          <li><strong>Berichtigungsrecht:</strong> Sie konnen die Berichtigung unrichtiger Daten verlangen.</li>
          <li><strong>Loschungsrecht:</strong> Sie konnen die Loschung Ihrer Daten verlangen.</li>
          <li><strong>Einschrankung der Verarbeitung:</strong> Sie konnen die Einschrankung der Verarbeitung verlangen.</li>
          <li><strong>Datenubertragbarkeit:</strong> Sie konnen Ihre Daten in einem gangigen Format erhalten.</li>
          <li><strong>Widerspruchsrecht:</strong> Sie konnen der Verarbeitung Ihrer Daten widersprechen.</li>
        </ul>
        <p className="text-neutral-600 mt-4">
          Da Ihre Chatveraufe nur lokal gespeichert werden, konnen Sie diese jederzeit selbst
          loschen, indem Sie die Browserdaten loschen oder die "Alle loschen"-Funktion in der
          Seitenleiste verwenden.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          6. Datensicherheit
        </h2>
        <p className="text-neutral-600">
          Wir setzen technische und organisatorische Sicherheitsmassnahmen ein, um Ihre Daten
          gegen zufallige oder vorsatzliche Manipulation, Verlust, Zerstorung oder den Zugriff
          unberechtigter Personen zu schutzen. Die Ubertragung von Daten erfolgt verschlusselt
          uber HTTPS.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          7. Kontakt fur Datenschutzanfragen
        </h2>
        <p className="text-neutral-600">
          Bei Fragen zum Datenschutz konnen Sie uns jederzeit kontaktieren:<br />
          E-Mail: <a href="mailto:datenschutz@fragdieleitlinie.de" className="text-brand-600 hover:underline">datenschutz@fragdieleitlinie.de</a>
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          8. Anderungen dieser Datenschutzerklarung
        </h2>
        <p className="text-neutral-600">
          Wir behalten uns vor, diese Datenschutzerklarung anzupassen, um sie an geanderte
          Rechtslagen oder bei Anderungen des Dienstes anzupassen. Die aktuelle Fassung ist
          stets auf dieser Seite verfugbar.
        </p>
        <p className="text-neutral-500 text-sm mt-4">
          Stand: Januar 2025
        </p>
      </section>
    </LegalLayout>
  );
};

export default Datenschutz;
