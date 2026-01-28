/**
 * Nutzungsbedingungen (Terms of Use) page.
 */

import React from 'react';
import { LegalLayout } from './LegalLayout';

export const Nutzungsbedingungen: React.FC = () => {
  return (
    <LegalLayout title="Nutzungsbedingungen">
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          1. Geltungsbereich
        </h2>
        <p className="text-neutral-600">
          Diese Nutzungsbedingungen gelten fur die Nutzung des Dienstes "Frag die Leitlinie"
          (nachfolgend "Dienst"), betrieben von HealthLingo UG (haftungsbeschrankt). Mit der
          Nutzung des Dienstes akzeptieren Sie diese Nutzungsbedingungen.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          2. Beschreibung des Dienstes
        </h2>
        <p className="text-neutral-600 mb-4">
          "Frag die Leitlinie" ist ein KI-basierter Informationsdienst, der Fragen zu
          medizinischen Leitlinien beantwortet. Der Dienst nutzt Kunstliche Intelligenz,
          um Informationen aus offentlich zuganglichen medizinischen Leitlinien
          zusammenzufassen und zu erlautern.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          3. Wichtiger Hinweis zur Nutzung
        </h2>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
          <p className="text-amber-800 font-medium mb-2">
            Keine medizinische Beratung
          </p>
          <p className="text-amber-700 text-sm">
            Die Antworten dieses Dienstes werden durch Kunstliche Intelligenz generiert
            und stellen <strong>keine medizinische Beratung, Diagnose oder Behandlungsempfehlung</strong> dar.
            Die bereitgestellten Informationen ersetzen nicht die professionelle Beratung
            durch einen qualifizierten Arzt oder medizinisches Fachpersonal.
          </p>
        </div>
        <p className="text-neutral-600">
          Bei gesundheitlichen Beschwerden, Symptomen oder Fragen zu Ihrer Gesundheit
          wenden Sie sich bitte immer an einen Arzt. Im Notfall rufen Sie den Notruf (112)
          oder suchen Sie die nachste Notaufnahme auf.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          4. KI-generierte Inhalte
        </h2>
        <p className="text-neutral-600 mb-4">
          Der Dienst verwendet ein Large Language Model (LLM) zur Generierung von Antworten.
          Bitte beachten Sie:
        </p>
        <ul className="list-disc list-inside text-neutral-600 space-y-2">
          <li>KI-generierte Antworten konnen ungenau oder fehlerhaft sein</li>
          <li>Die Antworten stellen keine Quelle erster Hand dar</li>
          <li>Medizinische Leitlinien andern sich - die KI hat moglicherweise nicht die aktuellsten Informationen</li>
          <li>Die Interpretation von Leitlinien erfordert medizinisches Fachwissen</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          5. Nutzerpflichten
        </h2>
        <p className="text-neutral-600 mb-4">
          Als Nutzer verpflichten Sie sich:
        </p>
        <ul className="list-disc list-inside text-neutral-600 space-y-2">
          <li>Den Dienst nur fur rechtmassige Zwecke zu nutzen</li>
          <li>Keine personenbezogenen Daten Dritter ohne deren Einwilligung einzugeben</li>
          <li>Den Dienst nicht zu missbrauchen oder zu uberlasten</li>
          <li>Die Antworten des Dienstes nicht als medizinische Beratung weiterzugeben</li>
        </ul>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          6. Haftungsbeschrankung
        </h2>
        <p className="text-neutral-600 mb-4">
          Der Betreiber haftet nicht fur:
        </p>
        <ul className="list-disc list-inside text-neutral-600 space-y-2">
          <li>Schaden, die durch die Nutzung oder Nichtnutzung der bereitgestellten Informationen entstehen</li>
          <li>Die Richtigkeit, Vollstandigkeit oder Aktualitat der KI-generierten Antworten</li>
          <li>Technische Storungen oder Ausfalle des Dienstes</li>
          <li>Datenverlust in localStorage des Browsers</li>
        </ul>
        <p className="text-neutral-600 mt-4">
          Die Haftung fur Vorsatz und grobe Fahrlassigkeit sowie fur Schaden aus der
          Verletzung des Lebens, des Korpers oder der Gesundheit bleibt unberuhrt.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          7. Verfugbarkeit
        </h2>
        <p className="text-neutral-600">
          Der Betreiber bemüht sich um eine hohe Verfugbarkeit des Dienstes, kann diese
          jedoch nicht garantieren. Der Dienst kann jederzeit ohne Vorankundigung geandert,
          unterbrochen oder eingestellt werden.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          8. Urheberrecht
        </h2>
        <p className="text-neutral-600">
          Die durch den Dienst generierten Antworten durfen fur personliche, nicht-kommerzielle
          Zwecke verwendet werden. Eine kommerzielle Nutzung bedarf der vorherigen schriftlichen
          Zustimmung des Betreibers.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          9. Anderungen der Nutzungsbedingungen
        </h2>
        <p className="text-neutral-600">
          Der Betreiber behalt sich vor, diese Nutzungsbedingungen jederzeit zu andern.
          Die geanderten Bedingungen werden auf dieser Seite veroffentlicht. Die weitere
          Nutzung des Dienstes nach Anderung der Bedingungen gilt als Zustimmung zu den
          geanderten Bedingungen.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-neutral-800 mb-4">
          10. Anwendbares Recht
        </h2>
        <p className="text-neutral-600">
          Es gilt deutsches Recht. Gerichtsstand ist, soweit gesetzlich zulassig, Berlin.
        </p>
        <p className="text-neutral-500 text-sm mt-4">
          Stand: Januar 2025
        </p>
      </section>
    </LegalLayout>
  );
};

export default Nutzungsbedingungen;
