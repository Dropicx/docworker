import React from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import Footer from '../components/Footer';

const Datenschutz: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <main className="flex-1">
        <div className="max-w-4xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
          <h1 className="text-3xl font-bold text-primary-900 mb-8">Datenschutzerklärung</h1>

          <div className="space-y-6 text-primary-700">
              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  1. Datenschutz auf einen Blick
                </h2>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Allgemeine Hinweise
                </h3>
                <p className="mb-4">
                  Die folgenden Hinweise geben einen einfachen Überblick darüber, was mit Ihren
                  personenbezogenen Daten passiert, wenn Sie diese Website besuchen.
                  Personenbezogene Daten sind alle Daten, mit denen Sie persönlich identifiziert
                  werden können.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Datenerfassung auf dieser Website
                </h3>
                <p className="mb-4">
                  <strong>Wer ist verantwortlich für die Datenerfassung auf dieser Website?</strong>
                  <br />
                  Die Datenverarbeitung auf dieser Website erfolgt durch den Websitebetreiber.
                  Dessen Kontaktdaten können Sie dem Impressum dieser Website entnehmen.
                </p>

                <p className="mb-4">
                  <strong>Anonyme Nutzung unseres Dienstes</strong>
                  <br />
                  Unser Übersetzungsdienst funktioniert vollständig anonym. Sie benötigen kein
                  Benutzerkonto und müssen sich nicht registrieren, um Dokumente zu übersetzen.
                  Wir speichern keine personenbezogenen Daten von Endnutzern. Die Verarbeitung
                  Ihrer Dokumente erfolgt ohne Zuordnung zu einer persönlichen Identität.
                </p>

                <p className="mb-4">
                  <strong>Wie erfassen wir Ihre Daten?</strong>
                  <br />
                  Die einzigen Daten, die wir erheben, sind die Dokumente, die Sie zur Übersetzung
                  hochladen. Diese werden ausschließlich für die Dauer der Verarbeitung temporär
                  gespeichert. Wir erfassen keine weiteren personenbezogenen Daten von Ihnen.
                </p>

                <p className="mb-4">
                  <strong>Wofür nutzen wir Ihre Daten?</strong>
                  <br />
                  Die hochgeladenen Dokumente werden ausschließlich zum Zweck der Übersetzung
                  verarbeitet. Nach Abschluss der Verarbeitung werden alle Daten automatisch
                  gelöscht. Es erfolgt keine dauerhafte Speicherung, keine Weitergabe an Dritte
                  und keine Nutzung für andere Zwecke.
                </p>

                <p className="mb-4">
                  <strong>Welche Rechte haben Sie bezüglich Ihrer Daten?</strong>
                  <br />
                  Da wir keine personenbezogenen Daten von Endnutzern speichern und die
                  Verarbeitung vollständig anonym erfolgt, sind die meisten DSGVO-Rechte (wie
                  Auskunft, Berichtigung, Löschung) nicht anwendbar. Ihre Dokumente werden
                  automatisch nach der Verarbeitung gelöscht, sodass keine Daten mehr vorhanden
                  sind, über die Auskunft erteilt werden könnte.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  2. Allgemeine Hinweise und Pflichtinformationen
                </h2>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Datenschutz</h3>
                <p className="mb-4">
                  Die Betreiber dieser Seiten nehmen den Schutz Ihrer persönlichen Daten sehr ernst.
                  Wir behandeln Ihre personenbezogenen Daten vertraulich und entsprechend den
                  gesetzlichen Datenschutzvorschriften sowie dieser Datenschutzerklärung.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Hinweis zur verantwortlichen Stelle
                </h3>
                <p className="mb-4">
                  Die verantwortliche Stelle für die Datenverarbeitung auf dieser Website ist im
                  Impressum angegeben. Verantwortliche Stelle ist die natürliche oder juristische
                  Person, die allein oder gemeinsam mit anderen über die Zwecke und Mittel der
                  Verarbeitung von personenbezogenen Daten entscheidet.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Speicherdauer</h3>
                <p className="mb-4">
                  Hochgeladene Dokumente und deren Übersetzungen werden nur für die Dauer der
                  Verarbeitung temporär gespeichert. Die Standard-Speicherdauer beträgt 24 Stunden
                  nach Abschluss der Verarbeitung (konfigurierbar, kann auf bis zu 0 Stunden
                  reduziert werden). Nach Ablauf dieser Frist werden alle Daten automatisch und
                  vollständig gelöscht:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>Das hochgeladene Originaldokument</li>
                  <li>Die extrahierten Texte (nach PII-Entfernung)</li>
                  <li>Die Übersetzungsergebnisse</li>
                  <li>Alle Verarbeitungsmetadaten</li>
                  <li>IP-Adressen (für Sicherheitsprotokollierung)</li>
                </ul>
                <p className="mb-4">
                  Diese kurze Speicherdauer ermöglicht es Ihnen, Ihre Übersetzung herunterzuladen,
                  während gleichzeitig der Datenschutz maximiert wird. Nach der Löschung sind die
                  Daten nicht mehr wiederherstellbar. Die automatische Löschung erfolgt durch
                  geplante Cleanup-Aufgaben, die stündlich ausgeführt werden.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  SSL- bzw. TLS-Verschlüsselung
                </h3>
                <p className="mb-4">
                  Diese Seite nutzt aus Sicherheitsgründen und zum Schutz der Übertragung
                  vertraulicher Inhalte, wie zum Beispiel medizinischer Dokumente, die Sie an uns
                  senden, eine SSL- bzw. TLS-Verschlüsselung. Eine verschlüsselte Verbindung
                  erkennen Sie daran, dass die Adresszeile des Browsers von &quot;http://&quot; auf
                  &quot;https://&quot; wechselt und an dem Schloss-Symbol in Ihrer Browserzeile.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  3. Datenerfassung auf dieser Website
                </h2>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Cookies</h3>
                <p className="mb-4">
                  <strong>Wir verwenden keine Cookies.</strong> Unser Dienst funktioniert vollständig
                  ohne Cookies. Wir setzen weder Tracking-Cookies noch Analyse-Cookies noch
                  Marketing-Cookies. Dies wird auch durch unser Cookie-freies Hinweis-Banner auf der
                  Website transparent kommuniziert.
                </p>
                <p className="mb-4">
                  Die einzige lokale Speicherung, die wir verwenden, ist der Browser-LocalStorage,
                  um Ihre Präferenz für das Cookie-Hinweis-Banner zu speichern (ob Sie das Banner
                  geschlossen haben). Diese Information wird nur lokal in Ihrem Browser gespeichert
                  und nicht an unseren Server übertragen.
                </p>
                <p className="mb-4">
                  Da wir keine Cookies verwenden, ist keine Cookie-Einwilligung erforderlich. Unser
                  Dienst respektiert Ihre Privatsphäre von Anfang an und verzichtet vollständig auf
                  Tracking und Analyse-Cookies.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Server-Log-Dateien
                </h3>
                <p className="mb-4">
                  Der Provider der Seiten erhebt und speichert automatisch Informationen in so
                  genannten Server-Log-Dateien, die Ihr Browser automatisch an uns übermittelt. Dies
                  sind:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>Browsertyp und Browserversion</li>
                  <li>Verwendetes Betriebssystem</li>
                  <li>Referrer URL</li>
                  <li>Hostname des zugreifenden Rechners</li>
                  <li>Uhrzeit der Serveranfrage</li>
                  <li>IP-Adresse</li>
                </ul>
                <p className="mb-4">
                  Eine Zusammenführung dieser Daten mit anderen Datenquellen wird nicht vorgenommen.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Verarbeitung medizinischer Dokumente
                </h3>
                <p className="mb-4">
                  Bei der Nutzung unseres Übersetzungsdienstes für medizinische Dokumente gelten
                  folgende Datenschutzmaßnahmen:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>
                    <strong>Automatische PII-Entfernung:</strong> Vor der Verarbeitung durch
                    KI-Systeme werden personenbezogene Informationen (Namen, Adressen, Telefonnummern,
                    Geburtsdaten, Versicherungsnummern) automatisch aus den Dokumenten entfernt. Dies
                    erfolgt lokal auf unseren Servern mit Hilfe von spaCy NER (Natural Entity
                    Recognition) und speziellen Mustern für deutsche medizinische Dokumente.
                  </li>
                  <li>
                    <strong>Temporäre Speicherung:</strong> Dokumente werden nur für die Dauer der
                    Verarbeitung (maximal 24 Stunden) temporär gespeichert
                  </li>
                  <li>
                    <strong>Automatische Löschung:</strong> Nach Abschluss der Übersetzung werden alle
                    Daten automatisch und vollständig gelöscht
                  </li>
                  <li>
                    <strong>Keine dauerhafte Speicherung:</strong> Es erfolgt keine dauerhafte
                    Speicherung von Dokumenten oder Übersetzungen
                  </li>
                  <li>
                    <strong>Keine Weitergabe:</strong> Keine Weitergabe der Daten an Dritte (außer
                    an den KI-Anbieter OVH für die Übersetzung, wobei nur PII-bereinigte Texte
                    übertragen werden)
                  </li>
                  <li>
                    <strong>Verschlüsselte Übertragung:</strong> Alle Daten werden über HTTPS/TLS
                    verschlüsselt übertragen
                  </li>
                  <li>
                    <strong>Verschlüsselung bei Speicherung:</strong> Administratorkonten (nicht
                    für Endnutzer) verwenden verschlüsselte Speicherung für E-Mail-Adressen und
                    Namen. Die Verschlüsselung von Dokumentinhalten ist geplant (siehe
                    technische Roadmap).
                  </li>
                  <li>
                    <strong>Keine Cookies:</strong> Unser Dienst verwendet keine Cookies und
                    speichert keine Tracking-Daten. Dies wird durch ein Cookie-freies
                    Hinweis-Banner auf der Website transparent kommuniziert.
                  </li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">4. Ihre Rechte</h2>

                <p className="mb-4">
                  Da unser Dienst vollständig anonym funktioniert und wir keine personenbezogenen
                  Daten von Endnutzern speichern, sind die meisten DSGVO-Rechte in diesem Kontext
                  nicht direkt anwendbar. Ihre Dokumente werden automatisch nach der Verarbeitung
                  gelöscht, sodass keine Daten mehr vorhanden sind, über die Auskunft erteilt
                  werden könnte.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Auskunftsrecht</h3>
                <p className="mb-4">
                  Da wir keine personenbezogenen Daten von Endnutzern speichern und die
                  Verarbeitung anonym erfolgt, können wir keine Auskunft über gespeicherte Daten
                  erteilen, da keine solchen Daten existieren. Falls Sie Fragen zum Thema
                  Datenschutz haben, können Sie sich jederzeit an uns wenden (siehe Kontakt im
                  Impressum).
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Recht auf Löschung
                </h3>
                <p className="mb-4">
                  Ihre hochgeladenen Dokumente werden automatisch nach 24 Stunden (oder früher)
                  gelöscht. Es ist keine manuelle Löschung erforderlich, da die Löschung
                  automatisch erfolgt. Falls Sie eine sofortige Löschung wünschen, können Sie sich
                  an uns wenden.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Recht auf Einschränkung der Verarbeitung
                </h3>
                <p className="mb-4">
                  Sie können jederzeit die Verarbeitung Ihrer Dokumente abbrechen, indem Sie den
                  Verarbeitungsprozess beenden, bevor die Übersetzung abgeschlossen ist. In diesem
                  Fall werden die Daten sofort gelöscht.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Recht auf Datenübertragbarkeit
                </h3>
                <p className="mb-4">
                  Da wir keine personenbezogenen Daten von Endnutzern speichern, gibt es keine
                  Daten, die übertragen werden könnten. Die Übersetzungsergebnisse können Sie
                  direkt nach der Verarbeitung herunterladen.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">
                  Beschwerderecht bei einer Aufsichtsbehörde
                </h3>
                <p className="mb-4">
                  Im Falle von Verstößen gegen die DSGVO steht Ihnen ein Beschwerderecht bei einer
                  Aufsichtsbehörde zu, insbesondere in dem Mitgliedstaat Ihres gewöhnlichen
                  Aufenthalts, Ihres Arbeitsplatzes oder des Orts des mutmaßlichen Verstoßes.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  6. Kontakt und Datenschutzanfragen
                </h2>
                <p className="mb-4">
                  Bei Fragen zum Datenschutz oder zur Ausübung Ihrer Rechte können Sie sich
                  jederzeit an uns wenden. Die Kontaktdaten finden Sie im{' '}
                  <Link
                    to="/impressum"
                    className="text-brand-600 hover:text-brand-700 underline font-medium"
                  >
                    Impressum
                  </Link>
                  .
                </p>
                <p className="mb-4">
                  <strong>Verantwortliche Stelle:</strong>
                  <br />
                  Die verantwortliche Stelle für die Datenverarbeitung ist im Impressum dieser
                  Website angegeben.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  7. Drittparteien und Datenverarbeitung
                </h2>
                <p className="mb-4">
                  Für die Bereitstellung unseres Dienstes nutzen wir folgende Drittanbieter:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>
                    <strong>OVH Cloud (EU):</strong> Für die KI-gestützte Übersetzung. Es werden
                    nur PII-bereinigte Texte an OVH übertragen. Die Datenverarbeitung erfolgt
                    ausschließlich in der EU.
                  </li>
                  <li>
                    <strong>Railway (EU):</strong> Für das Hosting der Anwendung und der
                    Datenbank. Railway ist SOC 2 Type I zertifiziert und bietet DSGVO-konforme
                    Data Processing Agreements.
                  </li>
                  <li>
                    <strong>PostgreSQL:</strong> Als Datenbanksystem. Die Datenbank wird in der EU
                    gehostet.
                  </li>
                </ul>
                <p className="mb-4">
                  Alle Datenverarbeitung erfolgt ausschließlich innerhalb der EU. Es finden keine
                  internationalen Datenübertragungen statt.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">
                  5. Besondere Hinweise zum Gesundheitsdatenschutz
                </h2>
                <p className="mb-4">
                  Da unser Dienst die Verarbeitung medizinischer Dokumente ermöglicht, die
                  möglicherweise Gesundheitsdaten enthalten, weisen wir besonders darauf hin:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>
                    Gesundheitsdaten gehören zu den besonderen Kategorien personenbezogener Daten
                    nach Art. 9 DSGVO
                  </li>
                  <li>
                    Wir verarbeiten diese Daten ausschließlich zum Zweck der Übersetzung und nur
                    nach Ihrer ausdrücklichen Einwilligung (durch das Akzeptieren der
                    Datenschutzerklärung beim Hochladen)
                  </li>
                  <li>
                    Die Verarbeitung erfolgt vollständig anonym - es werden keine
                    personenbezogenen Daten von Endnutzern gespeichert
                  </li>
                  <li>
                    Vor der KI-Verarbeitung werden alle personenbezogenen Informationen (Namen,
                    Adressen, Telefonnummern, etc.) automatisch entfernt
                  </li>
                  <li>
                    Es werden besondere technische und organisatorische Maßnahmen zum Schutz dieser
                    Daten getroffen (Verschlüsselung, kurze Speicherdauer, automatische Löschung)
                  </li>
                  <li>
                    Alle Daten werden nach maximal 24 Stunden automatisch und vollständig gelöscht
                  </li>
                </ul>
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

export default Datenschutz;
