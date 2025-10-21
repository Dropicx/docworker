import React, { useState, useEffect } from 'react';
import {
  ChevronDown,
  Shield,
  Lock,
  Clock,
  Database,
  Globe,
  FileText,
  AlertCircle,
} from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
  icon?: React.ElementType;
}

const FAQ: React.FC = () => {
  const [openItems, setOpenItems] = useState<Set<number>>(new Set());
  const [modelConfig, setModelConfig] = useState<{
    model_mapping: Record<string, string>;
    model_descriptions: Record<string, string>;
  } | null>(null);

  const toggleItem = (index: number) => {
    const newOpenItems = new Set(openItems);
    if (newOpenItems.has(index)) {
      newOpenItems.delete(index);
    } else {
      newOpenItems.add(index);
    }
    setOpenItems(newOpenItems);
  };

  // Load model configuration (only if authenticated)
  useEffect(() => {
    const loadModelConfiguration = async () => {
      // Check if we have auth token in sessionStorage
      const authToken = sessionStorage.getItem('settings_auth_token');
      if (!authToken) {
        // Not authenticated - use default, don't make request
        return;
      }

      try {
        const response = await fetch('/api/settings/model-configuration', {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        });
        if (response.ok) {
          const config = await response.json();
          setModelConfig(config);
        }
      } catch (error) {
        // Network errors or other issues - silently skip
        return;
      }
    };

    loadModelConfiguration();
  }, []);

  // Helper function to get current language translation model
  const getLanguageTranslationModel = (): string => {
    if (!modelConfig) return 'Llama 3.3';
    const model = modelConfig.model_mapping['language_translation_prompt'];
    if (!model) return 'Llama 3.3';

    // Format model name for display
    if (model.includes('Meta-Llama-3_3-70B-Instruct')) return 'Llama 3.3';
    if (model.includes('Mixtral')) return 'Mixtral';
    if (model.includes('mistral')) return 'Mistral';
    if (model.includes('qwen')) return 'Qwen';
    if (model.includes('Qwen')) return 'Qwen';

    // Default fallback - extract first part of model name
    return model.split('-')[0] || 'Llama 3.3';
  };

  const faqItems: FAQItem[] = [
    {
      question: 'Wo werden meine Daten verarbeitet und wie sicher ist das?',
      answer:
        'HealthLingo wird auf Railway.app gehostet, einem SOC 2 Type I zertifizierten Provider mit vollständiger DSGVO-Konformität. Die Server befinden sich in der EU und Railway bietet einen Data Processing Agreement (DPA) gemäß DSGVO Artikel 28. Die KI-Verarbeitung erfolgt über OVH AI Endpoints in europäischen Rechenzentren (ISO 27001, 27017, 27018, 27701 zertifiziert). OVH garantiert, dass Ihre Daten NIEMALS für das Training von KI-Modellen verwendet werden - alle Anfragen sind anonymisiert und werden nach der Verarbeitung sofort gelöscht.',
      icon: Shield,
    },
    {
      question: 'Werden meine medizinischen Daten gespeichert oder für KI-Training verwendet?',
      answer:
        'Nein, absolut nicht. HealthLingo speichert keinerlei Daten dauerhaft. OVH AI Endpoints hat eine strikte No-Training-Policy: Kundendaten werden niemals gespeichert oder für Modelltraining verwendet. Nach der Übersetzung werden alle Dokumente, Texte und persönlichen Informationen automatisch und unwiderruflich gelöscht. Die KI-Modelle lernen NICHT aus Ihren Daten - jede Anfrage ist isoliert und hinterlässt keine Spuren.',
      icon: Database,
    },
    {
      question: 'Wie lange dauert die Übersetzung?',
      answer:
        'Die meisten Dokumente werden innerhalb von 10-30 Sekunden übersetzt. Die genaue Dauer hängt von der Länge und Komplexität des Dokuments ab. Gescannte Dokumente können etwas länger dauern, da sie erst per OCR (Texterkennung) verarbeitet werden müssen.',
      icon: Clock,
    },
    {
      question: 'Welche Dateiformate werden unterstützt?',
      answer:
        'HealthLingo unterstützt PDF-Dateien (sowohl mit eingebettetem Text als auch gescannte Dokumente) sowie Bilddateien (JPG, PNG, JPEG). Die maximale Dateigröße beträgt 10 MB. Mehrseitige Dokumente werden vollständig verarbeitet.',
      icon: FileText,
    },
    {
      question: 'In welche Sprachen kann übersetzt werden?',
      answer: `Neben der Vereinfachung ins verständliche Deutsch unterstützen wir Übersetzungen in 19 sorgfältig ausgewählte Sprachen, die von ${getLanguageTranslationModel()} optimal unterstützt werden: Englisch, Französisch, Spanisch, Italienisch, Portugiesisch, Niederländisch, Russisch, Chinesisch, Japanisch, Koreanisch, Arabisch, Hindi, Polnisch, Tschechisch, Schwedisch, Norwegisch und Dänisch. Die Übersetzung erfolgt dabei immer zweistufig: erst Vereinfachung, dann präzise Übersetzung.`,
      icon: Globe,
    },
    {
      question: 'Was passiert mit persönlichen Daten im Dokument?',
      answer:
        'Persönliche Daten wie Namen, Adressen, Geburtsdaten und Versicherungsnummern werden automatisch erkannt und durch Platzhalter ersetzt (z.B. [NAME ENTFERNT]). Dies schützt Ihre Privatsphäre, während alle medizinischen Informationen vollständig erhalten bleiben. Die Anonymisierung erfolgt lokal, bevor Daten an die KI-Endpoints gesendet werden.',
      icon: Lock,
    },
    {
      question: 'Welche Sicherheitszertifizierungen haben die verwendeten Dienste?',
      answer:
        'Railway.app ist SOC 2 Type I zertifiziert (Type II folgt 2025) und bietet DSGVO-konforme Data Processing Agreements. OVH Cloud besitzt umfassende Zertifizierungen: ISO/IEC 27001 (Informationssicherheit), ISO/IEC 27017 (Cloud-Sicherheit), ISO/IEC 27018 (Datenschutz in der Cloud) und ISO/IEC 27701 (Datenschutz-Management). Beide Provider unterliegen europäischem Recht und garantieren, dass Ihre Daten die EU nicht verlassen.',
      icon: Shield,
    },
    {
      question: 'Ist die Übersetzung medizinisch korrekt?',
      answer:
        'HealthLingo verwendet fortschrittliche KI-Technologie, die speziell für medizinische Texte trainiert wurde. Die Übersetzungen sind sehr präzise, ersetzen jedoch keine professionelle medizinische Beratung. Bei wichtigen medizinischen Entscheidungen sollten Sie immer Ihren Arzt konsultieren.',
      icon: AlertCircle,
    },
    {
      question: 'Kann ich die Übersetzung herunterladen?',
      answer:
        'Ja, Sie können die übersetzte Version als PDF-Datei herunterladen. Das PDF enthält die vollständige Übersetzung in gut lesbarem Format mit Datum und Zeitstempel. Sie können den Text auch direkt in die Zwischenablage kopieren.',
      icon: FileText,
    },
    {
      question: 'Funktioniert HealthLingo mit gescannten Dokumenten?',
      answer:
        'Ja! HealthLingo verfügt über eine fortschrittliche Texterkennung (OCR) mit spezieller Optimierung für deutsche medizinische Dokumente. Auch handschriftliche Notizen, Tabellen und schlecht gescannte Dokumente werden zuverlässig erkannt und verarbeitet.',
      icon: FileText,
    },
    {
      question: 'Ist der Service wirklich kostenlos?',
      answer:
        'Ja, HealthLingo ist vollständig kostenlos nutzbar. Es gibt keine versteckten Kosten, keine Registrierung und keine Begrenzung der Anzahl der Übersetzungen. Unser Ziel ist es, medizinische Informationen für alle zugänglich zu machen.',
      icon: Shield,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="text-center space-y-4">
        <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-primary-900 via-brand-700 to-accent-700 bg-clip-text text-transparent">
          Häufig gestellte Fragen
        </h2>
        <p className="text-base sm:text-lg text-primary-600 max-w-3xl mx-auto">
          Alles was Sie über HealthLingo und die sichere Verarbeitung Ihrer medizinischen Dokumente
          wissen müssen
        </p>
      </div>

      {/* FAQ Accordion */}
      <div className="space-y-3 sm:space-y-4">
        {faqItems.map((item, index) => {
          const isOpen = openItems.has(index);
          const Icon = item.icon || Shield;

          return (
            <div key={index} className="card-elevated overflow-hidden transition-all duration-200">
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
