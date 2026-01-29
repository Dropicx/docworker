/**
 * Datenschutz (Privacy Policy) page - Required by GDPR.
 * Comprehensive privacy policy covering all data processors and services.
 */

import React from 'react';
import { LegalLayout } from './LegalLayout';

export const Datenschutz: React.FC = () => {
  return (
    <LegalLayout title="Datenschutzerklarung">
      {/* Introduction */}
      <section className="mb-8">
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Der Schutz Ihrer personenbezogenen Daten ist uns ein wichtiges Anliegen. Diese
          Datenschutzerklarung informiert Sie ausfuhrlich daruber, welche Daten wir erheben,
          wie wir sie verarbeiten und welche Rechte Sie haben. Wir verarbeiten Ihre Daten
          ausschliesslich auf Grundlage der gesetzlichen Bestimmungen (DSGVO, BDSG, TMG).
        </p>
      </section>

      {/* 1. Verantwortlicher */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          1. Verantwortlicher
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Verantwortlich fur die Datenverarbeitung auf dieser Website ist:
        </p>
        <address className="not-italic text-neutral-600 dark:text-neutral-400 leading-relaxed bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
          HealthLingo UG (haftungsbeschrankt)<br />
          Musterstrasse 123<br />
          10115 Berlin<br />
          Deutschland<br /><br />
          E-Mail: <a href="mailto:datenschutz@fragdieleitlinie.de" className="text-brand-600 dark:text-brand-400 hover:underline">datenschutz@fragdieleitlinie.de</a>
        </address>
      </section>

      {/* 2. Ubersicht der Datenverarbeitung */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          2. Ubersicht der Datenverarbeitung
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Bei der Nutzung von "Frag die Leitlinie" werden folgende Kategorien personenbezogener Daten verarbeitet:
        </p>

        <div className="space-y-4">
          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">2.1 Lokal gespeicherte Daten (Ihr Browser)</h3>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-1">
              <li><strong>Chatveraufe:</strong> Alle Ihre Unterhaltungen werden ausschliesslich in Ihrem Browser (localStorage) gespeichert</li>
              <li><strong>Einstellungen:</strong> Theme-Praferenzen (Hell/Dunkel), UI-Einstellungen</li>
              <li><strong>Vorgeschlagene Fragen:</strong> Follow-up-Fragen werden lokal zwischengespeichert</li>
            </ul>
            <p className="text-sm text-neutral-500 dark:text-neutral-500 mt-2">
              Diese Daten verlassen niemals Ihren Browser und werden nicht an unsere Server ubertragen.
            </p>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">2.2 Verarbeitete Daten (Server)</h3>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-1">
              <li><strong>Chat-Nachrichten:</strong> Ihre Fragen werden zur Verarbeitung an unsere Server ubertragen</li>
              <li><strong>Feedback:</strong> Wenn Sie eine Antwort bewerten (Daumen hoch/runter), wird dieses Feedback gespeichert</li>
              <li><strong>Technische Metadaten:</strong> IP-Adresse, User-Agent, Zugriffszeiten</li>
            </ul>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">2.3 Automatisch erhobene Daten</h3>
            <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-1">
              <li>IP-Adresse (wird durch Cloudflare anonymisiert)</li>
              <li>Browsertyp und -version</li>
              <li>Betriebssystem</li>
              <li>Referrer-URL</li>
              <li>Datum und Uhrzeit des Zugriffs</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 3. Rechtsgrundlagen */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          3. Rechtsgrundlagen der Verarbeitung
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Die Verarbeitung Ihrer Daten erfolgt auf Basis folgender Rechtsgrundlagen:
        </p>
        <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2">
          <li>
            <strong>Art. 6 Abs. 1 lit. b DSGVO (Vertragserfullung):</strong> Verarbeitung Ihrer
            Chat-Nachrichten zur Erbringung unseres Dienstes
          </li>
          <li>
            <strong>Art. 6 Abs. 1 lit. f DSGVO (Berechtigte Interessen):</strong> Technische
            Protokollierung zur Gewahrleistung der IT-Sicherheit und Systemstabilitat
          </li>
          <li>
            <strong>Art. 6 Abs. 1 lit. a DSGVO (Einwilligung):</strong> Sofern Sie uns eine
            ausdruckliche Einwilligung erteilen (z.B. fur Feedback)
          </li>
        </ul>
      </section>

      {/* 4. Auftragsverarbeiter und Drittanbieter */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          4. Auftragsverarbeiter und Drittanbieter
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Zur Erbringung unseres Dienstes setzen wir folgende Auftragsverarbeiter ein:
        </p>

        <div className="space-y-6">
          {/* Cloudflare */}
          <div className="border-l-4 border-brand-500 pl-4">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
              4.1 Cloudflare, Inc.
            </h3>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400">
              <tbody>
                <tr><td className="font-medium pr-4 py-1">Zweck:</td><td>CDN, DDoS-Schutz, DNS-Verwaltung, SSL/TLS-Verschlusselung</td></tr>
                <tr><td className="font-medium pr-4 py-1">Daten:</td><td>IP-Adresse, HTTP-Request-Daten, Performance-Metriken</td></tr>
                <tr><td className="font-medium pr-4 py-1">Standort:</td><td>Global verteilt (EU-Rechenzentren bevorzugt)</td></tr>
                <tr><td className="font-medium pr-4 py-1">Rechtsgrundlage:</td><td>Art. 6 Abs. 1 lit. f DSGVO, EU-Standardvertragsklauseln</td></tr>
                <tr><td className="font-medium pr-4 py-1">Datenschutz:</td><td><a href="https://www.cloudflare.com/privacypolicy/" className="text-brand-600 dark:text-brand-400 hover:underline" target="_blank" rel="noopener noreferrer">cloudflare.com/privacypolicy</a></td></tr>
              </tbody>
            </table>
          </div>

          {/* Hetzner / Dify */}
          <div className="border-l-4 border-green-500 pl-4">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
              4.2 Hetzner Online GmbH (Dify-Backend)
            </h3>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400">
              <tbody>
                <tr><td className="font-medium pr-4 py-1">Zweck:</td><td>Hosting der KI-Anwendung (Dify), RAG-Verarbeitung, Vektordatenbank</td></tr>
                <tr><td className="font-medium pr-4 py-1">Daten:</td><td>Chat-Nachrichten, Konversations-IDs, Zeitstempel</td></tr>
                <tr><td className="font-medium pr-4 py-1">Standort:</td><td>Deutschland (Falkenstein/Nurnberg)</td></tr>
                <tr><td className="font-medium pr-4 py-1">Rechtsgrundlage:</td><td>Art. 6 Abs. 1 lit. b DSGVO, Art. 28 DSGVO (AVV)</td></tr>
                <tr><td className="font-medium pr-4 py-1">Datenschutz:</td><td><a href="https://www.hetzner.com/de/rechtliches/datenschutz" className="text-brand-600 dark:text-brand-400 hover:underline" target="_blank" rel="noopener noreferrer">hetzner.com/datenschutz</a></td></tr>
              </tbody>
            </table>
            <p className="text-sm text-green-700 dark:text-green-400 mt-2">
              Deutsches Rechenzentrum - vollstandige DSGVO-Konformitat
            </p>
          </div>

          {/* Railway */}
          <div className="border-l-4 border-purple-500 pl-4">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
              4.3 Railway Corporation
            </h3>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400">
              <tbody>
                <tr><td className="font-medium pr-4 py-1">Zweck:</td><td>Hosting der Frontend-Anwendung und API-Gateway</td></tr>
                <tr><td className="font-medium pr-4 py-1">Daten:</td><td>HTTP-Requests, Zugriffsprotokolle</td></tr>
                <tr><td className="font-medium pr-4 py-1">Standort:</td><td>USA (mit EU-Standardvertragsklauseln)</td></tr>
                <tr><td className="font-medium pr-4 py-1">Rechtsgrundlage:</td><td>Art. 6 Abs. 1 lit. f DSGVO, EU-Standardvertragsklauseln</td></tr>
                <tr><td className="font-medium pr-4 py-1">Datenschutz:</td><td><a href="https://railway.app/legal/privacy" className="text-brand-600 dark:text-brand-400 hover:underline" target="_blank" rel="noopener noreferrer">railway.app/legal/privacy</a></td></tr>
              </tbody>
            </table>
            <div className="bg-amber-50 dark:bg-amber-900/20 p-3 rounded mt-2">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>Drittlandtransfer:</strong> Die Ubermittlung in die USA erfolgt auf Grundlage
                von EU-Standardvertragsklauseln gem. Art. 46 Abs. 2 lit. c DSGVO.
              </p>
            </div>
          </div>

          {/* Mistral AI */}
          <div className="border-l-4 border-blue-500 pl-4">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
              4.4 Mistral AI (KI-Modell)
            </h3>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400">
              <tbody>
                <tr><td className="font-medium pr-4 py-1">Zweck:</td><td>Generierung von Antworten auf Basis medizinischer Leitlinien</td></tr>
                <tr><td className="font-medium pr-4 py-1">Modell:</td><td>Mistral Large</td></tr>
                <tr><td className="font-medium pr-4 py-1">Daten:</td><td>Chat-Nachrichten (anonymisiert), Kontext aus Leitlinien</td></tr>
                <tr><td className="font-medium pr-4 py-1">Standort:</td><td>Frankreich / Europaische Union</td></tr>
                <tr><td className="font-medium pr-4 py-1">Rechtsgrundlage:</td><td>Art. 6 Abs. 1 lit. b DSGVO</td></tr>
                <tr><td className="font-medium pr-4 py-1">Datenschutz:</td><td><a href="https://mistral.ai/terms/#privacy-policy" className="text-brand-600 dark:text-brand-400 hover:underline" target="_blank" rel="noopener noreferrer">mistral.ai/terms</a></td></tr>
              </tbody>
            </table>
            <p className="text-sm text-blue-700 dark:text-blue-400 mt-2">
              Franzosisches Unternehmen - Verarbeitung innerhalb der EU
            </p>
          </div>

          {/* Amazon Web Services */}
          <div className="border-l-4 border-orange-500 pl-4">
            <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
              4.5 Amazon Web Services (AWS)
            </h3>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400">
              <tbody>
                <tr><td className="font-medium pr-4 py-1">Zweck:</td><td>Text-Embeddings (Titan) und Reranking fur Dokumentensuche</td></tr>
                <tr><td className="font-medium pr-4 py-1">Dienste:</td><td>Amazon Titan Embeddings, Amazon Rerank</td></tr>
                <tr><td className="font-medium pr-4 py-1">Daten:</td><td>Suchanfragen (anonymisiert), Textfragmente</td></tr>
                <tr><td className="font-medium pr-4 py-1">Standort:</td><td>EU (Frankfurt, eu-central-1)</td></tr>
                <tr><td className="font-medium pr-4 py-1">Rechtsgrundlage:</td><td>Art. 6 Abs. 1 lit. b DSGVO, AWS GDPR DPA</td></tr>
                <tr><td className="font-medium pr-4 py-1">Datenschutz:</td><td><a href="https://aws.amazon.com/privacy/" className="text-brand-600 dark:text-brand-400 hover:underline" target="_blank" rel="noopener noreferrer">aws.amazon.com/privacy</a></td></tr>
              </tbody>
            </table>
            <p className="text-sm text-green-700 dark:text-green-400 mt-2">
              Nutzung des EU-Rechenzentrums Frankfurt - Daten verbleiben in der EU
            </p>
          </div>
        </div>
      </section>

      {/* 5. KI-Verarbeitung */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          5. Besondere Hinweise zur KI-Verarbeitung
        </h2>

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
          <h3 className="font-medium text-blue-800 dark:text-blue-200 mb-2">Transparenzhinweis gem. Art. 22 DSGVO</h3>
          <p className="text-blue-700 dark:text-blue-300 text-sm">
            Dieser Dienst verwendet automatisierte Entscheidungsfindung in Form von Large Language Models (LLMs).
            Die KI generiert Antworten basierend auf Ihren Eingaben und abgerufenen Leitlinien-Dokumenten.
            Es findet <strong>kein Profiling</strong> im Sinne des Art. 22 DSGVO statt.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">5.1 Keine Verwendung fur KI-Training</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Ihre Chat-Nachrichten werden <strong>nicht</strong> fur das Training oder Fine-Tuning von
              KI-Modellen verwendet. Wir nutzen ausschliesslich vortrainierte Modelle unserer Partner.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">5.2 Speicherdauer bei KI-Diensten</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Chat-Nachrichten werden nach der Verarbeitung nicht persistent bei den KI-Anbietern gespeichert.
              Temporare Logs werden innerhalb von 30 Tagen automatisch geloscht.
            </p>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">5.3 RAG-System (Retrieval Augmented Generation)</h3>
            <p className="text-neutral-600 dark:text-neutral-400">
              Ihre Anfragen werden verwendet, um relevante Abschnitte aus medizinischen Leitlinien abzurufen.
              Diese Suche erfolgt uber Vektorembeddings (Amazon Titan) und semantisches Ranking (Amazon Rerank).
              Es werden keine personenbezogenen Daten in der Vektordatenbank gespeichert.
            </p>
          </div>
        </div>
      </section>

      {/* 6. Cookies und Speichertechnologien */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          6. Cookies und lokale Speichertechnologien
        </h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">6.1 Cookies</h3>
            <p className="text-neutral-600 dark:text-neutral-400 mb-2">
              Diese Website verwendet <strong>keine Tracking-Cookies</strong> und keine Cookies von Drittanbietern
              zu Werbezwecken. Es werden lediglich technisch notwendige Cookies eingesetzt:
            </p>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700 rounded">
              <thead className="bg-neutral-100 dark:bg-neutral-800">
                <tr>
                  <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-700">Cookie</th>
                  <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-700">Zweck</th>
                  <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-700">Dauer</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">__cf_bm</td>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">Cloudflare Bot-Schutz</td>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">30 Minuten</td>
                </tr>
                <tr>
                  <td className="p-2">cf_clearance</td>
                  <td className="p-2">Cloudflare Sicherheitsprufung</td>
                  <td className="p-2">1 Jahr</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div>
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">6.2 LocalStorage</h3>
            <p className="text-neutral-600 dark:text-neutral-400 mb-2">
              Folgende Daten werden in Ihrem Browser gespeichert und verlassen niemals Ihr Gerat:
            </p>
            <table className="w-full text-sm text-neutral-600 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700 rounded">
              <thead className="bg-neutral-100 dark:bg-neutral-800">
                <tr>
                  <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-700">Schlussel</th>
                  <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-700">Inhalt</th>
                  <th className="text-left p-2 border-b border-neutral-200 dark:border-neutral-700">Loschung</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">chat-history</td>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">Ihre Chatveraufe</td>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">Manuell uber "Alle loschen"</td>
                </tr>
                <tr>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">theme</td>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">Hell/Dunkel-Modus</td>
                  <td className="p-2 border-b border-neutral-200 dark:border-neutral-700">Manuell</td>
                </tr>
                <tr>
                  <td className="p-2">hideAiDisclaimer</td>
                  <td className="p-2">KI-Hinweis ausgeblendet</td>
                  <td className="p-2">Manuell</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 7. Datensicherheit */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          7. Datensicherheit
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Wir setzen umfangreiche technische und organisatorische Massnahmen ein:
        </p>
        <ul className="list-disc list-inside text-neutral-600 dark:text-neutral-400 space-y-2">
          <li><strong>Verschlusselung:</strong> Alle Datenubertragungen erfolgen uber TLS 1.3 (HTTPS)</li>
          <li><strong>DDoS-Schutz:</strong> Cloudflare Web Application Firewall</li>
          <li><strong>Zugriffskontrolle:</strong> Mehrstufige Authentifizierung fur alle Systeme</li>
          <li><strong>Monitoring:</strong> Kontinuierliche Uberwachung auf Sicherheitsvorfalle</li>
          <li><strong>Datensparsamkeit:</strong> Erhebung nur der minimal notwendigen Daten</li>
          <li><strong>Anonymisierung:</strong> IP-Adressen werden nach kurzer Zeit anonymisiert</li>
        </ul>
      </section>

      {/* 8. Ihre Rechte */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          8. Ihre Rechte nach DSGVO
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Sie haben folgende Rechte bezuglich Ihrer personenbezogenen Daten:
        </p>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Auskunftsrecht (Art. 15)</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Sie konnen Auskunft uber Ihre gespeicherten Daten verlangen.
            </p>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Berichtigung (Art. 16)</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Sie konnen die Berichtigung unrichtiger Daten verlangen.
            </p>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Loschung (Art. 17)</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Sie konnen die Loschung Ihrer Daten verlangen ("Recht auf Vergessenwerden").
            </p>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Einschrankung (Art. 18)</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Sie konnen die Einschrankung der Verarbeitung verlangen.
            </p>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Datenubertragbarkeit (Art. 20)</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Sie konnen Ihre Daten in einem gangigen Format erhalten.
            </p>
          </div>

          <div className="bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
            <h3 className="font-medium text-neutral-800 dark:text-neutral-200 mb-2">Widerspruch (Art. 21)</h3>
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              Sie konnen der Verarbeitung Ihrer Daten widersprechen.
            </p>
          </div>
        </div>

        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 mt-4">
          <h3 className="font-medium text-green-800 dark:text-green-200 mb-2">Praktischer Hinweis</h3>
          <p className="text-green-700 dark:text-green-300 text-sm">
            Da Ihre Chatveraufe nur lokal in Ihrem Browser gespeichert werden, konnen Sie diese jederzeit
            selbst loschen: Nutzen Sie die "Alle loschen"-Funktion in der Seitenleiste oder loschen Sie
            Ihre Browser-Daten.
          </p>
        </div>
      </section>

      {/* 9. Beschwerderecht */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          9. Beschwerderecht bei der Aufsichtsbehorde
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-4">
          Wenn Sie der Ansicht sind, dass die Verarbeitung Ihrer Daten gegen das Datenschutzrecht
          verstosst, haben Sie das Recht, sich bei einer Aufsichtsbehorde zu beschweren.
          Die fur uns zustandige Aufsichtsbehorde ist:
        </p>
        <address className="not-italic text-neutral-600 dark:text-neutral-400 leading-relaxed bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg">
          Berliner Beauftragte fur Datenschutz und Informationsfreiheit<br />
          Alt-Moabit 59-61<br />
          10555 Berlin<br />
          Telefon: +49 30 13889-0<br />
          E-Mail: mailbox@datenschutz-berlin.de
        </address>
      </section>

      {/* 10. Speicherdauer */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          10. Speicherdauer
        </h2>
        <table className="w-full text-sm text-neutral-600 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-700 rounded">
          <thead className="bg-neutral-100 dark:bg-neutral-800">
            <tr>
              <th className="text-left p-3 border-b border-neutral-200 dark:border-neutral-700">Datenkategorie</th>
              <th className="text-left p-3 border-b border-neutral-200 dark:border-neutral-700">Speicherdauer</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">Chat-Nachrichten (Server)</td>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">Keine dauerhafte Speicherung, nur wahrend der Session</td>
            </tr>
            <tr>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">Chatveraufe (localStorage)</td>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">Bis zur manuellen Loschung durch Sie</td>
            </tr>
            <tr>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">Server-Logs (Cloudflare)</td>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">72 Stunden</td>
            </tr>
            <tr>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">Feedback-Daten</td>
              <td className="p-3 border-b border-neutral-200 dark:border-neutral-700">30 Tage fur Qualitatsverbesserungen</td>
            </tr>
            <tr>
              <td className="p-3">KI-Verarbeitungslogs</td>
              <td className="p-3">Max. 30 Tage (durch Anbieter)</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* 11. Kontakt */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          11. Kontakt fur Datenschutzanfragen
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Bei Fragen zum Datenschutz oder zur Ausubung Ihrer Rechte kontaktieren Sie uns bitte:<br /><br />
          E-Mail: <a href="mailto:datenschutz@fragdieleitlinie.de" className="text-brand-600 dark:text-brand-400 hover:underline">datenschutz@fragdieleitlinie.de</a>
          <br /><br />
          Wir werden Ihre Anfrage innerhalb von 30 Tagen bearbeiten.
        </p>
      </section>

      {/* 12. Anderungen */}
      <section>
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-100 mb-4">
          12. Anderungen dieser Datenschutzerklarung
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Wir behalten uns vor, diese Datenschutzerklarung anzupassen, um sie an geanderte
          Rechtslagen oder bei Anderungen des Dienstes anzupassen. Die aktuelle Fassung ist
          stets auf dieser Seite verfugbar. Bei wesentlichen Anderungen werden wir Sie
          gesondert informieren.
        </p>
        <p className="text-neutral-500 dark:text-neutral-500 text-sm mt-4">
          Stand: Januar 2025
        </p>
      </section>
    </LegalLayout>
  );
};

export default Datenschutz;
