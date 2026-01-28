/**
 * Nutzungsbedingungen (Terms of Use) page.
 * Comprehensive terms covering AI usage, medical disclaimers, and liability.
 */

import React from 'react';
import { LegalLayout } from './LegalLayout';

export const Nutzungsbedingungen: React.FC = () => {
  return (
    <LegalLayout title="Nutzungsbedingungen">
      {/* Introduction */}
      <section className="mb-8">
        <p className="text-neutral-600 dark:text-neutral-400">
          Willkommen bei "Frag die Leitlinie". Bitte lesen Sie diese Nutzungsbedingungen sorgfaltig durch,
          bevor Sie unseren Dienst nutzen. Mit der Nutzung des Dienstes erklaren Sie sich mit diesen
          Bedingungen einverstanden.
        </p>
      </section>

      {/* 1. Geltungsbereich */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          1. Geltungsbereich und Vertragspartner
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Diese Nutzungsbedingungen gelten fur die Nutzung des Dienstes "Frag die Leitlinie"
          (nachfolgend "Dienst"), betrieben von:
        </p>
        <address className="not-italic text-neutral-600 dark:text-neutral-400 leading-relaxed bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
          HealthLingo UG (haftungsbeschrankt)<br />
          Musterstrasse 123<br />
          10115 Berlin<br />
          Deutschland
        </address>
        <p className="text-neutral-600 dark:text-neutral-400 mt-4">
          Mit der Nutzung des Dienstes akzeptieren Sie diese Nutzungsbedingungen in der jeweils
          gultigen Fassung. Widersprechen Sie diesen Bedingungen, durfen Sie den Dienst nicht nutzen.
        </p>
      </section>

      {/* 2. Beschreibung des Dienstes */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          2. Beschreibung des Dienstes
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          "Frag die Leitlinie" ist ein KI-basierter Informationsdienst, der Fragen zu
          deutschen medizinischen Leitlinien (AWMF) beantwortet. Der Dienst:
        </p>
        <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2 mb-4">
          <li>Nutzt Kunstliche Intelligenz (Large Language Models) zur Generierung von Antworten</li>
          <li>Durchsucht eine Datenbank mit offentlich zuganglichen medizinischen Leitlinien</li>
          <li>Fasst relevante Informationen aus den Leitlinien zusammen</li>
          <li>Nennt Quellen und Empfehlungsgrade, soweit verfugbar</li>
        </ul>

        <div className="bg-neutral-100 dark:bg-neutral-800 p-4 rounded-lg">
          <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Technische Komponenten</h3>
          <ul className="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
            <li><strong>KI-Modell:</strong> Mistral Large (franzosischer Anbieter, EU-Verarbeitung)</li>
            <li><strong>Dokumentensuche:</strong> RAG-System mit Amazon Titan Embeddings</li>
            <li><strong>Relevanz-Ranking:</strong> Amazon Rerank</li>
            <li><strong>Backend:</strong> Dify auf Hetzner (deutsches Rechenzentrum)</li>
          </ul>
        </div>
      </section>

      {/* 3. WICHTIGER MEDIZINISCHER HINWEIS */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          3. Wichtiger medizinischer Hinweis
        </h2>

        <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-700 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-bold text-red-800 dark:text-red-200 mb-3">
            KEINE MEDIZINISCHE BERATUNG
          </h3>
          <div className="text-red-700 dark:text-red-300 space-y-3">
            <p>
              <strong>Die Antworten dieses Dienstes stellen KEINE medizinische Beratung, Diagnose
              oder Behandlungsempfehlung dar.</strong>
            </p>
            <p>
              Die bereitgestellten Informationen werden durch Kunstliche Intelligenz generiert
              und konnen unvollstandig, veraltet oder fehlerhaft sein.
            </p>
            <p>
              <strong>Dieser Dienst ersetzt NICHT:</strong>
            </p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Die Konsultation eines qualifizierten Arztes</li>
              <li>Die Beratung durch medizinisches Fachpersonal</li>
              <li>Eine professionelle medizinische Diagnose</li>
              <li>Eine individuelle Behandlungsempfehlung</li>
            </ul>
          </div>
        </div>

        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg p-4 mb-4">
          <h3 className="font-medium text-amber-800 dark:text-amber-200 mb-2">Notfalle</h3>
          <p className="text-amber-700 dark:text-amber-300">
            Bei lebensbedrohlichen Zustanden oder medizinischen Notfallen rufen Sie sofort den
            <strong> Notruf 112</strong> an oder suchen Sie die nachste Notaufnahme auf.
            Nutzen Sie diesen Dienst NICHT in Notfallsituationen.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">3.1 Zielgruppe</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Dieser Dienst richtet sich primar an medizinisches Fachpersonal (Arzte, Pflegekrafte,
              Therapeuten) zur schnellen Recherche in medizinischen Leitlinien. Laien sollten
              die Informationen nur als allgemeine Orientierung verstehen und immer einen Arzt
              konsultieren.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">3.2 Leitlinien sind Empfehlungen</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Medizinische Leitlinien sind systematisch entwickelte Entscheidungshilfen, keine
              bindenden Vorschriften. Die Anwendung auf den Einzelfall obliegt stets dem
              behandelnden Arzt unter Berucksichtigung der individuellen Patientensituation.
            </p>
          </div>
        </div>
      </section>

      {/* 4. KI-generierte Inhalte */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          4. KI-generierte Inhalte und deren Grenzen
        </h2>

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
          <h3 className="font-medium text-blue-800 dark:text-blue-200 mb-2">Transparenzhinweis</h3>
          <p className="text-blue-700 dark:text-blue-300 text-sm">
            Alle Antworten dieses Dienstes werden durch ein Large Language Model (LLM) generiert.
            Wir kennzeichnen alle Antworten als KI-generiert.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">4.1 Bekannte Limitierungen</h3>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2">
              <li><strong>Halluzinationen:</strong> KI-Modelle konnen plausibel klingende, aber faktisch falsche Informationen generieren</li>
              <li><strong>Veraltete Informationen:</strong> Die Leitlinien-Datenbank wird regelmasig aktualisiert, kann aber nicht immer den aktuellsten Stand widerspiegeln</li>
              <li><strong>Kontextverlust:</strong> Bei komplexen Fragen kann relevanter Kontext verloren gehen</li>
              <li><strong>Interpretationsfehler:</strong> Die KI kann Leitlinien falsch interpretieren oder vereinfachen</li>
              <li><strong>Fehlende Quellen:</strong> Nicht alle Aussagen konnen zuverlassig einer Quelle zugeordnet werden</li>
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">4.2 Qualitatsverbesserung</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Wir arbeiten kontinuierlich an der Verbesserung der Antwortqualitat durch:
            </p>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-1 mt-2">
              <li>Regelmasige Aktualisierung der Leitlinien-Datenbank</li>
              <li>Optimierung der Suchparameter (Embeddings, Reranking)</li>
              <li>Auswertung von Nutzerfeedback</li>
              <li>Validierung durch medizinisches Fachpersonal</li>
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">4.3 Keine Gewahrleistung</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Wir ubernehmen keine Gewahrleistung fur die Richtigkeit, Vollstandigkeit, Aktualitat
              oder Eignung der KI-generierten Antworten fur einen bestimmten Zweck.
            </p>
          </div>
        </div>
      </section>

      {/* 5. Nutzerpflichten */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          5. Pflichten und Verantwortung des Nutzers
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">5.1 Allgemeine Pflichten</h3>
            <p className="text-neutral-600 dark:text-neutral-400 mb-2">
              Als Nutzer verpflichten Sie sich:
            </p>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2">
              <li>Den Dienst nur fur rechtmassige Zwecke zu nutzen</li>
              <li>Keine personenbezogenen Daten Dritter (insbesondere Patientendaten) ohne Einwilligung einzugeben</li>
              <li>Den Dienst nicht zu missbrauchen oder systematisch zu uberlasten</li>
              <li>Keine automatisierten Anfragen (Bots, Scraper) ohne schriftliche Genehmigung zu senden</li>
              <li>Die Antworten nicht als originare arztliche Beratung weiterzugeben</li>
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">5.2 Verantwortung fur medizinische Entscheidungen</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              <strong>Sie tragen die alleinige Verantwortung</strong> fur alle medizinischen
              Entscheidungen, die Sie auf Basis der durch diesen Dienst bereitgestellten
              Informationen treffen. Es obliegt Ihnen, die Informationen durch Konsultation
              der Original-Leitlinien und/oder eines qualifizierten Arztes zu verifizieren.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">5.3 Datenschutz bei Eingaben</h3>
            <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-lg">
              <p className="text-amber-700 dark:text-amber-300 text-sm">
                <strong>Hinweis:</strong> Geben Sie keine personenbezogenen Patientendaten, keine
                Namen, Geburtsdaten oder andere identifizierbare Informationen in den Chat ein.
                Formulieren Sie Fragen allgemein und ohne Bezug auf konkrete Personen.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Haftungsbeschrankung */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          6. Haftungsbeschrankung und Haftungsausschluss
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">6.1 Umfang der Haftung</h3>
            <p className="text-neutral-600 dark:text-neutral-400 mb-2">
              Der Betreiber haftet <strong>nicht</strong> fur:
            </p>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2">
              <li>Schaden, die durch die Nutzung oder Nichtnutzung der bereitgestellten Informationen entstehen</li>
              <li>Schaden durch fehlerhafte, unvollstandige oder veraltete KI-generierte Antworten</li>
              <li>Gesundheitsschaden, die auf Basis der Informationen dieses Dienstes entstehen</li>
              <li>Entscheidungen, die Nutzer auf Basis der bereitgestellten Informationen treffen</li>
              <li>Technische Storungen, Ausfalle oder Datenverlust</li>
              <li>Verlust von Chatveraufen im localStorage des Browsers</li>
              <li>Handlungen oder Unterlassungen von Drittanbietern (KI-Dienste, Hosting)</li>
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">6.2 Zwingende gesetzliche Haftung</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Die vorstehenden Haftungsbeschrankungen gelten nicht fur:
            </p>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-1 mt-2">
              <li>Vorsatzlich oder grob fahrlassig verursachte Schaden</li>
              <li>Schaden aus der Verletzung des Lebens, des Korpers oder der Gesundheit</li>
              <li>Haftung nach dem Produkthaftungsgesetz</li>
              <li>Sonstige zwingende gesetzliche Haftungstatbestande</li>
            </ul>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">6.3 Haftungshochstgrenze</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Soweit die Haftung nicht ausgeschlossen ist, ist diese auf den typischerweise
              vorhersehbaren Schaden begrenzt. Da dieser Dienst kostenlos angeboten wird,
              ist die Haftung auf Falle von Vorsatz und grober Fahrlassigkeit beschrankt.
            </p>
          </div>
        </div>
      </section>

      {/* 7. Geistiges Eigentum */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          7. Geistiges Eigentum und Urheberrecht
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">7.1 Eigentum des Betreibers</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Die Website, ihre Gestaltung, Logos, Texte und Software sind urheberrechtlich
              geschutzt und Eigentum des Betreibers oder lizenziert.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">7.2 Medizinische Leitlinien</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Die medizinischen Leitlinien sind Eigentum der jeweiligen Fachgesellschaften
              und werden uber die AWMF (Arbeitsgemeinschaft der Wissenschaftlichen Medizinischen
              Fachgesellschaften) veroffentlicht. Wir verweisen auf die Originalquellen und
              erheben keinen Anspruch auf deren Inhalte.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">7.3 Nutzung der Antworten</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Die KI-generierten Antworten durfen fur personliche, nicht-kommerzielle Zwecke
              verwendet werden. Eine kommerzielle Nutzung, Weiterverbreitung oder systematische
              Speicherung bedarf der vorherigen schriftlichen Zustimmung des Betreibers.
            </p>
          </div>
        </div>
      </section>

      {/* 8. Verfugbarkeit und Anderungen */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          8. Verfugbarkeit und Anderungen des Dienstes
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">8.1 Keine Verfugbarkeitsgarantie</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Der Betreiber bemuht sich um eine hohe Verfugbarkeit des Dienstes, kann diese
              jedoch nicht garantieren. Der Dienst kann insbesondere durch:
            </p>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-1 mt-2">
              <li>Wartungsarbeiten</li>
              <li>Technische Storungen bei Drittanbietern</li>
              <li>Uberlastung</li>
              <li>Hohere Gewalt</li>
            </ul>
            <p className="text-neutral-600 dark:text-neutral-400 mt-2">
              vorubergehend nicht verfugbar sein.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">8.2 Anderungen und Einstellung</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Der Betreiber behalt sich vor, den Dienst jederzeit ohne Vorankundigung zu
              andern, zu erweitern, einzuschranken oder einzustellen. Es besteht kein
              Anspruch auf fortgesetzten Betrieb des Dienstes in seiner aktuellen Form.
            </p>
          </div>
        </div>
      </section>

      {/* 9. Datenschutz */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          9. Datenschutz
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Informationen zur Verarbeitung personenbezogener Daten finden Sie in unserer{' '}
          <a href="/datenschutz" className="text-brand-600 dark:text-brand-400 hover:underline">
            Datenschutzerklarung
          </a>.
          Diese ist integraler Bestandteil dieser Nutzungsbedingungen.
        </p>
      </section>

      {/* 10. Drittanbieter */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          10. Drittanbieter und externe Dienste
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Dieser Dienst nutzt externe Dienstleister fur den Betrieb:
        </p>
        <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2">
          <li><strong>Cloudflare:</strong> CDN, DDoS-Schutz, DNS (USA, mit EU-Standardvertragsklauseln)</li>
          <li><strong>Hetzner:</strong> Server-Hosting fur Dify-Backend (Deutschland)</li>
          <li><strong>Railway:</strong> Frontend-Hosting (USA, mit EU-Standardvertragsklauseln)</li>
          <li><strong>Mistral AI:</strong> KI-Sprachmodell (Frankreich/EU)</li>
          <li><strong>Amazon Web Services:</strong> Titan Embeddings, Rerank (EU-Region Frankfurt)</li>
        </ul>
        <p className="text-neutral-600 dark:text-neutral-400 mt-4">
          Der Betreiber haftet nicht fur Ausfalle, Datenverluste oder Fehlverhalten dieser
          Drittanbieter, soweit dies gesetzlich zulassig ist.
        </p>
      </section>

      {/* 11. Anderungen der Nutzungsbedingungen */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          11. Anderungen der Nutzungsbedingungen
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Der Betreiber behalt sich vor, diese Nutzungsbedingungen jederzeit zu andern.
          Die geanderten Bedingungen werden auf dieser Seite veroffentlicht. Die weitere
          Nutzung des Dienstes nach Veroffentlichung der Anderungen gilt als Zustimmung
          zu den geanderten Bedingungen. Bei wesentlichen Anderungen werden registrierte
          Nutzer gesondert informiert.
        </p>
      </section>

      {/* 12. Schlussbestimmungen */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          12. Schlussbestimmungen
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">12.1 Anwendbares Recht</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des
              UN-Kaufrechts (CISG).
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">12.2 Gerichtsstand</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Gerichtsstand fur alle Streitigkeiten ist, soweit gesetzlich zulassig, Berlin.
              Fur Verbraucher gilt der allgemeine Gerichtsstand am Wohnsitz.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">12.3 Salvatorische Klausel</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Sollten einzelne Bestimmungen dieser Nutzungsbedingungen unwirksam sein oder
              werden, beruhrt dies die Wirksamkeit der ubrigen Bestimmungen nicht. An die
              Stelle unwirksamer Bestimmungen treten die gesetzlichen Regelungen.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">12.4 Online-Streitbeilegung</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Die Europaische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS)
              bereit:{' '}
              <a
                href="https://ec.europa.eu/consumers/odr"
                className="text-brand-600 dark:text-brand-400 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                https://ec.europa.eu/consumers/odr
              </a>
              <br />
              Wir sind nicht verpflichtet und nicht bereit, an einem Streitbeilegungsverfahren
              vor einer Verbraucherschlichtungsstelle teilzunehmen.
            </p>
          </div>
        </div>
      </section>

      {/* 13. Kontakt */}
      <section>
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          13. Kontakt
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Bei Fragen zu diesen Nutzungsbedingungen kontaktieren Sie uns bitte unter:<br /><br />
          E-Mail: <a href="mailto:kontakt@fragdieleitlinie.de" className="text-brand-600 dark:text-brand-400 hover:underline">kontakt@fragdieleitlinie.de</a>
        </p>
        <p className="text-neutral-500 dark:text-neutral-500 text-sm mt-6">
          Stand: Januar 2025
        </p>
      </section>
    </LegalLayout>
  );
};

export default Nutzungsbedingungen;
