import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

const Nutzungsbedingungen: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-brand-50/10 to-accent-50/10">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Link
          to="/"
          className="inline-flex items-center text-primary-600 hover:text-primary-700 mb-8 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Zurück zur Startseite
        </Link>

        <div className="card-elevated">
          <div className="card-body">
            <h1 className="text-3xl font-bold text-primary-900 mb-8">Nutzungsbedingungen</h1>

            <div className="space-y-6 text-primary-700">
              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">§ 1 Geltungsbereich</h2>
                <p className="mb-4">
                  (1) Diese Nutzungsbedingungen gelten für die Nutzung des medizinischen
                  Dokumentenübersetzungsdienstes (nachfolgend &quot;Dienst&quot; genannt) auf dieser
                  Website.
                </p>
                <p className="mb-4">
                  (2) Mit der Nutzung des Dienstes erklären Sie sich mit diesen Nutzungsbedingungen
                  einverstanden. Wenn Sie mit diesen Bedingungen nicht einverstanden sind, nutzen
                  Sie bitte unseren Dienst nicht.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 2 Leistungsbeschreibung
                </h2>
                <p className="mb-4">
                  (1) Unser Dienst bietet eine automatisierte Übersetzung medizinischer Dokumente in
                  vereinfachte, verständliche Sprache sowie in andere Sprachen.
                </p>
                <p className="mb-4">
                  (2) Die Übersetzungen werden durch künstliche Intelligenz erstellt und dienen
                  ausschließlich zur Information und zum besseren Verständnis medizinischer Inhalte.
                </p>
                <p className="mb-4">
                  (3) Die Übersetzungen ersetzen keine professionelle medizinische Beratung,
                  Diagnose oder Behandlung.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 3 Nutzungsbedingungen
                </h2>
                <p className="mb-4">
                  (1) Der Dienst darf nur für persönliche, nicht-kommerzielle Zwecke genutzt werden.
                </p>
                <p className="mb-4">
                  (2) Sie verpflichten sich, den Dienst nur für rechtmäßige Zwecke zu nutzen und
                  keine Inhalte hochzuladen, die:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>Rechte Dritter verletzen</li>
                  <li>Gegen geltendes Recht verstoßen</li>
                  <li>Schadsoftware oder schädlichen Code enthalten</li>
                  <li>Die Funktionsfähigkeit des Dienstes beeinträchtigen könnten</li>
                </ul>
                <p className="mb-4">
                  (3) Die systematische Abfrage oder Extraktion von Daten ist untersagt.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 4 Medizinischer Haftungsausschluss
                </h2>
                <p className="mb-4 font-semibold text-error-700 bg-error-50 p-4 rounded-lg">
                  WICHTIGER HINWEIS: Die bereitgestellten Übersetzungen sind NICHT als medizinischer
                  Rat zu verstehen!
                </p>
                <p className="mb-4">
                  (1) Die Übersetzungen werden automatisch durch künstliche Intelligenz erstellt und
                  können Fehler, Ungenauigkeiten oder Missverständnisse enthalten.
                </p>
                <p className="mb-4">
                  (2) Die Übersetzungen dürfen niemals als Grundlage für medizinische Entscheidungen
                  verwendet werden.
                </p>
                <p className="mb-4">
                  (3) Bei medizinischen Fragen oder Problemen konsultieren Sie immer einen
                  qualifizierten Arzt oder Gesundheitsdienstleister.
                </p>
                <p className="mb-4">
                  (4) Im Notfall kontaktieren Sie sofort den Notruf (112) oder suchen Sie die
                  nächste Notaufnahme auf.
                </p>
                <p className="mb-4">
                  (5) Verlassen Sie sich niemals ausschließlich auf die Übersetzungen dieses
                  Dienstes für gesundheitsbezogene Entscheidungen.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 5 Haftungsbeschränkung
                </h2>
                <p className="mb-4">
                  (1) Wir übernehmen keine Haftung für die Richtigkeit, Vollständigkeit oder
                  Aktualität der Übersetzungen.
                </p>
                <p className="mb-4">
                  (2) Jegliche Haftung für Schäden, die direkt oder indirekt aus der Nutzung des
                  Dienstes entstehen, wird ausgeschlossen, soweit gesetzlich zulässig.
                </p>
                <p className="mb-4">
                  (3) Dies gilt nicht für Schäden aus der Verletzung des Lebens, des Körpers oder
                  der Gesundheit sowie für sonstige Schäden, die auf einer vorsätzlichen oder grob
                  fahrlässigen Pflichtverletzung beruhen.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">§ 6 Datenschutz</h2>
                <p className="mb-4">
                  (1) Die Verarbeitung personenbezogener Daten erfolgt gemäß unserer
                  Datenschutzerklärung.
                </p>
                <p className="mb-4">
                  (2) Hochgeladene Dokumente werden nur für die Dauer der Verarbeitung temporär
                  gespeichert und anschließend automatisch gelöscht.
                </p>
                <p className="mb-4">
                  (3) Es erfolgt keine dauerhafte Speicherung oder Weitergabe Ihrer Dokumente an
                  Dritte.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 7 Geistiges Eigentum
                </h2>
                <p className="mb-4">
                  (1) Alle Rechte an der Website und dem Dienst, einschließlich Urheberrechte,
                  Markenrechte und andere gewerbliche Schutzrechte, verbleiben bei uns.
                </p>
                <p className="mb-4">
                  (2) Die Nutzung des Dienstes gewährt Ihnen keine Rechte an unserem geistigen
                  Eigentum, außer den in diesen Nutzungsbedingungen ausdrücklich eingeräumten
                  Rechten.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">§ 8 Verfügbarkeit</h2>
                <p className="mb-4">
                  (1) Wir bemühen uns um eine hohe Verfügbarkeit des Dienstes, können diese jedoch
                  nicht garantieren.
                </p>
                <p className="mb-4">
                  (2) Wir behalten uns vor, den Dienst jederzeit zu ändern, zu unterbrechen oder
                  einzustellen.
                </p>
                <p className="mb-4">
                  (3) Wartungsarbeiten werden, soweit möglich, im Voraus angekündigt.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 9 Änderungen der Nutzungsbedingungen
                </h2>
                <p className="mb-4">
                  (1) Wir behalten uns vor, diese Nutzungsbedingungen jederzeit zu ändern.
                </p>
                <p className="mb-4">
                  (2) Änderungen werden auf dieser Seite veröffentlicht. Die fortgesetzte Nutzung
                  des Dienstes nach Veröffentlichung von Änderungen gilt als Zustimmung zu den
                  geänderten Bedingungen.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 10 Anwendbares Recht und Gerichtsstand
                </h2>
                <p className="mb-4">
                  (1) Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des
                  UN-Kaufrechts.
                </p>
                <p className="mb-4">
                  (2) Gerichtsstand für alle Streitigkeiten aus oder im Zusammenhang mit diesen
                  Nutzungsbedingungen ist, soweit gesetzlich zulässig, [Ihr Gerichtsstand].
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  § 11 Salvatorische Klausel
                </h2>
                <p className="mb-4">
                  Sollten einzelne Bestimmungen dieser Nutzungsbedingungen unwirksam oder
                  undurchführbar sein oder werden, bleibt die Wirksamkeit der übrigen Bestimmungen
                  hiervon unberührt.
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
        </div>
      </div>
    </div>
  );
};

export default Nutzungsbedingungen;
