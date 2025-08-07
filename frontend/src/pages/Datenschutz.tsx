import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

const Datenschutz: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-brand-50/10 to-accent-50/10">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Link to="/" className="inline-flex items-center text-primary-600 hover:text-primary-700 mb-8 transition-colors">
          <ArrowLeft className="w-5 h-5 mr-2" />
          Zurück zur Startseite
        </Link>
        
        <div className="card-elevated">
          <div className="card-body">
            <h1 className="text-3xl font-bold text-primary-900 mb-8">Datenschutzerklärung</h1>
            
            <div className="space-y-6 text-primary-700">
              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">1. Datenschutz auf einen Blick</h2>
                
                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Allgemeine Hinweise</h3>
                <p className="mb-4">
                  Die folgenden Hinweise geben einen einfachen Überblick darüber, was mit Ihren 
                  personenbezogenen Daten passiert, wenn Sie diese Website besuchen. Personenbezogene 
                  Daten sind alle Daten, mit denen Sie persönlich identifiziert werden können.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Datenerfassung auf dieser Website</h3>
                <p className="mb-4">
                  <strong>Wer ist verantwortlich für die Datenerfassung auf dieser Website?</strong><br />
                  Die Datenverarbeitung auf dieser Website erfolgt durch den Websitebetreiber. 
                  Dessen Kontaktdaten können Sie dem Impressum dieser Website entnehmen.
                </p>

                <p className="mb-4">
                  <strong>Wie erfassen wir Ihre Daten?</strong><br />
                  Ihre Daten werden zum einen dadurch erhoben, dass Sie uns diese mitteilen. Hierbei 
                  kann es sich z.B. um Daten handeln, die Sie in ein Kontaktformular eingeben oder 
                  bei der Nutzung unseres Übersetzungsdienstes hochladen.
                </p>

                <p className="mb-4">
                  <strong>Wofür nutzen wir Ihre Daten?</strong><br />
                  Die Daten werden ausschließlich dazu erhoben, um die Übersetzungsdienstleistung 
                  bereitzustellen. Nach der Verarbeitung werden die Daten automatisch gelöscht.
                </p>

                <p className="mb-4">
                  <strong>Welche Rechte haben Sie bezüglich Ihrer Daten?</strong><br />
                  Sie haben jederzeit das Recht, unentgeltlich Auskunft über Herkunft, Empfänger und 
                  Zweck Ihrer gespeicherten personenbezogenen Daten zu erhalten. Sie haben außerdem 
                  ein Recht, die Berichtigung oder Löschung dieser Daten zu verlangen.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">2. Allgemeine Hinweise und Pflichtinformationen</h2>
                
                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Datenschutz</h3>
                <p className="mb-4">
                  Die Betreiber dieser Seiten nehmen den Schutz Ihrer persönlichen Daten sehr ernst. 
                  Wir behandeln Ihre personenbezogenen Daten vertraulich und entsprechend den gesetzlichen 
                  Datenschutzvorschriften sowie dieser Datenschutzerklärung.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Hinweis zur verantwortlichen Stelle</h3>
                <p className="mb-4">
                  Die verantwortliche Stelle für die Datenverarbeitung auf dieser Website ist im Impressum 
                  angegeben. Verantwortliche Stelle ist die natürliche oder juristische Person, die allein 
                  oder gemeinsam mit anderen über die Zwecke und Mittel der Verarbeitung von personenbezogenen 
                  Daten entscheidet.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Speicherdauer</h3>
                <p className="mb-4">
                  Soweit innerhalb dieser Datenschutzerklärung keine speziellere Speicherdauer genannt wurde, 
                  verbleiben Ihre personenbezogenen Daten bei uns, bis der Zweck für die Datenverarbeitung 
                  entfällt. Bei unserem Übersetzungsdienst werden hochgeladene Dokumente und deren Übersetzungen 
                  nicht dauerhaft gespeichert und nach der Verarbeitung automatisch gelöscht.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">SSL- bzw. TLS-Verschlüsselung</h3>
                <p className="mb-4">
                  Diese Seite nutzt aus Sicherheitsgründen und zum Schutz der Übertragung vertraulicher 
                  Inhalte, wie zum Beispiel medizinischer Dokumente, die Sie an uns senden, eine SSL- bzw. 
                  TLS-Verschlüsselung. Eine verschlüsselte Verbindung erkennen Sie daran, dass die 
                  Adresszeile des Browsers von "http://" auf "https://" wechselt und an dem Schloss-Symbol 
                  in Ihrer Browserzeile.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">3. Datenerfassung auf dieser Website</h2>
                
                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Cookies</h3>
                <p className="mb-4">
                  Unsere Internetseiten verwenden so genannte "Cookies". Cookies sind kleine Datenpakete 
                  und richten auf Ihrem Endgerät keinen Schaden an. Sie werden entweder vorübergehend für 
                  die Dauer einer Sitzung (Session-Cookies) oder dauerhaft (permanente Cookies) auf Ihrem 
                  Endgerät gespeichert. Session-Cookies werden nach Ende Ihres Besuchs automatisch gelöscht.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Server-Log-Dateien</h3>
                <p className="mb-4">
                  Der Provider der Seiten erhebt und speichert automatisch Informationen in so genannten 
                  Server-Log-Dateien, die Ihr Browser automatisch an uns übermittelt. Dies sind:
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

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Verarbeitung medizinischer Dokumente</h3>
                <p className="mb-4">
                  Bei der Nutzung unseres Übersetzungsdienstes für medizinische Dokumente:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>Dokumente werden nur für die Dauer der Verarbeitung temporär gespeichert</li>
                  <li>Nach Abschluss der Übersetzung werden alle Daten automatisch gelöscht</li>
                  <li>Es erfolgt keine dauerhafte Speicherung von Dokumenten oder Übersetzungen</li>
                  <li>Keine Weitergabe der Daten an Dritte</li>
                  <li>Verschlüsselte Übertragung aller Daten</li>
                </ul>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">4. Ihre Rechte</h2>
                
                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Auskunftsrecht</h3>
                <p className="mb-4">
                  Sie haben das Recht, jederzeit Auskunft über Ihre bei uns gespeicherten personenbezogenen 
                  Daten zu erhalten. Hierzu sowie zu weiteren Fragen zum Thema Datenschutz können Sie sich 
                  jederzeit an uns wenden.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Recht auf Löschung</h3>
                <p className="mb-4">
                  Sie haben das Recht, die unverzügliche Löschung Ihrer personenbezogenen Daten zu verlangen, 
                  soweit die Verarbeitung nicht zur Erfüllung einer rechtlichen Verpflichtung erforderlich ist.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Recht auf Einschränkung der Verarbeitung</h3>
                <p className="mb-4">
                  Sie haben das Recht, die Einschränkung der Verarbeitung Ihrer personenbezogenen Daten zu 
                  verlangen.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Recht auf Datenübertragbarkeit</h3>
                <p className="mb-4">
                  Sie haben das Recht, Daten, die wir auf Grundlage Ihrer Einwilligung oder in Erfüllung 
                  eines Vertrags automatisiert verarbeiten, an sich oder an einen Dritten in einem gängigen, 
                  maschinenlesbaren Format aushändigen zu lassen.
                </p>

                <h3 className="text-lg font-semibold text-primary-800 mt-4 mb-2">Beschwerderecht bei einer Aufsichtsbehörde</h3>
                <p className="mb-4">
                  Im Falle von Verstößen gegen die DSGVO steht den Betroffenen ein Beschwerderecht bei einer 
                  Aufsichtsbehörde, insbesondere in dem Mitgliedstaat ihres gewöhnlichen Aufenthalts, ihres 
                  Arbeitsplatzes oder des Orts des mutmaßlichen Verstoßes zu.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold text-primary-900 mb-3">5. Besondere Hinweise zum Gesundheitsdatenschutz</h2>
                <p className="mb-4">
                  Da unser Dienst die Verarbeitung medizinischer Dokumente ermöglicht, die möglicherweise 
                  Gesundheitsdaten enthalten, weisen wir besonders darauf hin:
                </p>
                <ul className="list-disc list-inside mb-4 ml-4">
                  <li>Gesundheitsdaten gehören zu den besonderen Kategorien personenbezogener Daten</li>
                  <li>Wir verarbeiten diese Daten ausschließlich zum Zweck der Übersetzung</li>
                  <li>Die Verarbeitung erfolgt nur mit Ihrer ausdrücklichen Einwilligung</li>
                  <li>Alle Mitarbeiter sind zur Verschwiegenheit verpflichtet</li>
                  <li>Es werden besondere technische und organisatorische Maßnahmen zum Schutz dieser Daten getroffen</li>
                </ul>
              </section>

              <section className="pt-4 border-t border-primary-200">
                <p className="text-sm text-primary-600">
                  Stand: {new Date().toLocaleDateString('de-DE', { year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              </section>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Datenschutz;