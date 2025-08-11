import React, { useState } from 'react';
import { ChevronDown, Shield, Lock, Clock, Database, Globe, FileText, AlertCircle } from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
  icon?: React.ElementType;
}

const FAQ: React.FC = () => {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());

  const toggleItem = (index: number) => {
    const newOpenItems = new Set(openItems);
    if (newOpenItems.has(index)) {
      newOpenItems.delete(index);
    } else {
      newOpenItems.add(index);
    }
    setOpenItems(newOpenItems);
  };

  const faqItems: FAQItem[] = [
    {
      question: "Wie werden meine Daten verarbeitet?",
      answer: "Ihre Dokumente werden ausschließlich für die Übersetzung verarbeitet und sofort nach Abschluss vollständig gelöscht. Es findet keine dauerhafte Speicherung statt. Die Verarbeitung erfolgt verschlüsselt auf deutschen Servern und entspricht vollständig der DSGVO. Ihre Daten verlassen niemals die EU.",
      icon: Shield
    },
    {
      question: "Werden meine medizinischen Daten gespeichert?",
      answer: "Nein, absolut nicht. HealthLingo speichert keinerlei Daten. Nach der Übersetzung werden alle Dokumente, Texte und persönlichen Informationen automatisch und unwiderruflich von unseren Servern gelöscht. Es gibt keine Datenbank mit Ihren medizinischen Informationen.",
      icon: Database
    },
    {
      question: "Wie lange dauert die Übersetzung?",
      answer: "Die meisten Dokumente werden innerhalb von 10-30 Sekunden übersetzt. Die genaue Dauer hängt von der Länge und Komplexität des Dokuments ab. Gescannte Dokumente können etwas länger dauern, da sie erst per OCR (Texterkennung) verarbeitet werden müssen.",
      icon: Clock
    },
    {
      question: "Welche Dateiformate werden unterstützt?",
      answer: "HealthLingo unterstützt PDF-Dateien (sowohl mit eingebettetem Text als auch gescannte Dokumente) sowie Bilddateien (JPG, PNG, JPEG). Die maximale Dateigröße beträgt 10 MB. Mehrseitige Dokumente werden vollständig verarbeitet.",
      icon: FileText
    },
    {
      question: "In welche Sprachen kann übersetzt werden?",
      answer: "Neben der Vereinfachung ins verständliche Deutsch unterstützen wir Übersetzungen in über 30 Sprachen, darunter Englisch, Französisch, Türkisch, Arabisch, Russisch, Polnisch, Spanisch und viele mehr. Die Übersetzung erfolgt dabei immer zweistufig: erst Vereinfachung, dann Übersetzung.",
      icon: Globe
    },
    {
      question: "Was passiert mit persönlichen Daten im Dokument?",
      answer: "Persönliche Daten wie Namen, Adressen, Geburtsdaten und Versicherungsnummern werden automatisch erkannt und durch Platzhalter ersetzt (z.B. [NAME ENTFERNT]). Dies schützt Ihre Privatsphäre, während alle medizinischen Informationen vollständig erhalten bleiben.",
      icon: Lock
    },
    {
      question: "Ist die Übersetzung medizinisch korrekt?",
      answer: "HealthLingo verwendet fortschrittliche KI-Technologie, die speziell für medizinische Texte trainiert wurde. Die Übersetzungen sind sehr präzise, ersetzen jedoch keine professionelle medizinische Beratung. Bei wichtigen medizinischen Entscheidungen sollten Sie immer Ihren Arzt konsultieren.",
      icon: AlertCircle
    },
    {
      question: "Kann ich die Übersetzung herunterladen?",
      answer: "Ja, Sie können die übersetzte Version als PDF-Datei herunterladen. Das PDF enthält die vollständige Übersetzung in gut lesbarem Format mit Datum und Zeitstempel. Sie können den Text auch direkt in die Zwischenablage kopieren.",
      icon: FileText
    },
    {
      question: "Funktioniert HealthLingo mit gescannten Dokumenten?",
      answer: "Ja! HealthLingo verfügt über eine fortschrittliche Texterkennung (OCR) mit spezieller Optimierung für deutsche medizinische Dokumente. Auch handschriftliche Notizen, Tabellen und schlecht gescannte Dokumente werden zuverlässig erkannt und verarbeitet.",
      icon: FileText
    },
    {
      question: "Ist der Service wirklich kostenlos?",
      answer: "Ja, HealthLingo ist vollständig kostenlos nutzbar. Es gibt keine versteckten Kosten, keine Registrierung und keine Begrenzung der Anzahl der Übersetzungen. Unser Ziel ist es, medizinische Informationen für alle zugänglich zu machen.",
      icon: Shield
    }
  ];

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="text-center space-y-4">
        <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-primary-900 via-brand-700 to-accent-700 bg-clip-text text-transparent">
          Häufig gestellte Fragen
        </h2>
        <p className="text-base sm:text-lg text-primary-600 max-w-3xl mx-auto">
          Alles was Sie über HealthLingo und die sichere Verarbeitung Ihrer medizinischen Dokumente wissen müssen
        </p>
      </div>

      {/* FAQ Accordion */}
      <div className="space-y-3 sm:space-y-4">
        {faqItems.map((item, index) => {
          const isOpen = openItems.has(index);
          const Icon = item.icon || Shield;
          
          return (
            <div
              key={index}
              className="card-elevated overflow-hidden transition-all duration-200"
            >
              <button
                onClick={() => toggleItem(index)}
                className="w-full px-4 sm:px-6 py-4 sm:py-5 flex items-start space-x-3 sm:space-x-4 hover:bg-neutral-50 transition-colors duration-150"
                aria-expanded={isOpen}
                aria-controls={`faq-answer-${index}`}
              >
                {/* Icon */}
                <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-brand-100 to-accent-100 rounded-lg sm:rounded-xl flex items-center justify-center">
                  <Icon className="w-4 h-4 sm:w-5 sm:h-5 text-brand-600" />
                </div>
                
                {/* Question and Arrow */}
                <div className="flex-1 text-left">
                  <h3 className="text-sm sm:text-base lg:text-lg font-semibold text-primary-900 pr-2">
                    {item.question}
                  </h3>
                </div>
                
                {/* Chevron */}
                <div className="flex-shrink-0">
                  <ChevronDown 
                    className={`w-5 h-5 sm:w-6 sm:h-6 text-primary-400 transition-transform duration-200 ${
                      isOpen ? 'rotate-180' : ''
                    }`}
                  />
                </div>
              </button>
              
              {/* Answer */}
              <div
                id={`faq-answer-${index}`}
                className={`overflow-hidden transition-all duration-300 ${
                  isOpen ? 'max-h-96' : 'max-h-0'
                }`}
              >
                <div className="px-4 sm:px-6 pb-4 sm:pb-5 pl-12 sm:pl-16 lg:pl-20">
                  <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                    {item.answer}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom CTA */}
      <div className="text-center pt-4 sm:pt-6">
        <p className="text-sm sm:text-base text-primary-600">
          Haben Sie weitere Fragen?{' '}
          <a 
            href="mailto:support@healthlingo.de" 
            className="text-brand-600 hover:text-brand-700 font-medium underline underline-offset-2"
          >
            Kontaktieren Sie uns
          </a>
        </p>
      </div>
    </div>
  );
};

export default FAQ;