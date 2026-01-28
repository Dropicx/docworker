/**
 * Impressum (Legal Notice) page - Required by German TMG §5.
 */

import React from 'react';
import { LegalLayout } from './LegalLayout';

export const Impressum: React.FC = () => {
  return (
    <LegalLayout title="Impressum">
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          Angaben gemass § 5 TMG
        </h2>
        <address className="not-italic text-neutral-600 leading-relaxed">
          HealthLingo UG (haftungsbeschrankt)<br />
          Musterstrasse 123<br />
          10115 Berlin<br />
          Deutschland
        </address>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">Kontakt</h2>
        <p className="text-neutral-600">
          E-Mail: <a href="mailto:kontakt@fragdieleitlinie.de" className="text-brand-600 hover:underline">kontakt@fragdieleitlinie.de</a>
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          Verantwortlich fur den Inhalt nach § 55 Abs. 2 RStV
        </h2>
        <address className="not-italic text-neutral-600 leading-relaxed">
          [Name des Verantwortlichen]<br />
          Musterstrasse 123<br />
          10115 Berlin
        </address>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          Haftungsausschluss
        </h2>

        <h3 className="text-lg font-medium text-neutral-700 mb-2">Haftung fur Inhalte</h3>
        <p className="text-neutral-600 mb-4">
          Die Inhalte unserer Seiten wurden mit grosster Sorgfalt erstellt. Fur die Richtigkeit,
          Vollstandigkeit und Aktualitat der Inhalte konnen wir jedoch keine Gewahr ubernehmen.
        </p>

        <h3 className="text-lg font-medium text-neutral-700 mb-2">Medizinischer Hinweis</h3>
        <p className="text-neutral-600 mb-4">
          <strong>Wichtig:</strong> Die durch diesen Dienst bereitgestellten Informationen werden
          durch Kunstliche Intelligenz generiert und stellen keine medizinische Beratung dar.
          Die Antworten basieren auf medizinischen Leitlinien, ersetzen jedoch keinesfalls die
          Konsultation eines qualifizierten Arztes oder medizinischen Fachpersonals. Bei
          gesundheitlichen Beschwerden oder Fragen zu Ihrer Gesundheit wenden Sie sich bitte
          immer an einen Arzt.
        </p>

        <h3 className="text-lg font-medium text-neutral-700 mb-2">Haftung fur Links</h3>
        <p className="text-neutral-600">
          Unser Angebot enthalt Links zu externen Webseiten Dritter, auf deren Inhalte wir
          keinen Einfluss haben. Deshalb konnen wir fur diese fremden Inhalte auch keine
          Gewahr ubernehmen.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">Urheberrecht</h2>
        <p className="text-neutral-600">
          Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten
          unterliegen dem deutschen Urheberrecht. Die Vervielfaltigung, Bearbeitung,
          Verbreitung und jede Art der Verwertung ausserhalb der Grenzen des Urheberrechtes
          bedurfen der schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.
        </p>
      </section>
    </LegalLayout>
  );
};

export default Impressum;
