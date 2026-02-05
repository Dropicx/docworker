import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, Lock, Clock, Database, Globe, FileText, AlertCircle } from 'lucide-react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

interface FAQItem {
  question: string;
  answer: string;
  icon?: React.ElementType;
}

const FAQ: React.FC = () => {
  const { t } = useTranslation();
  const [modelConfig, setModelConfig] = useState<{
    model_mapping: Record<string, string>;
    model_descriptions: Record<string, string>;
  } | null>(null);

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

  const faqIcons = [Shield, Database, Clock, FileText, Globe, Lock, Shield, AlertCircle, FileText, FileText, Shield];

  const faqItems = faqIcons.map((icon, index) => ({
    question: t(`faq.items.${index}.question`),
    answer: index === 4
      ? t(`faq.items.${index}.answer`, { model: getLanguageTranslationModel() })
      : t(`faq.items.${index}.answer`),
    icon,
  }));

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="text-center space-y-4">
        <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold bg-gradient-to-r from-primary-900 via-brand-700 to-accent-700 bg-clip-text text-transparent">
          {t('faq.title')}
        </h2>
        <p className="text-base sm:text-lg text-primary-600 max-w-3xl mx-auto">
          {t('faq.subtitle')}
        </p>
      </div>

      {/* FAQ Accordion (shadcn) */}
      <Accordion type="multiple" className="space-y-3 sm:space-y-4">
        {faqItems.map((item, index) => {
          const Icon = item.icon || Shield;

          return (
            <AccordionItem
              key={index}
              value={`item-${index}`}
              className="bg-white rounded-xl sm:rounded-2xl shadow-soft border border-primary-100/50 overflow-hidden transition-all duration-200 hover:shadow-medium px-0 data-[state=open]:shadow-medium"
            >
              <AccordionTrigger className="px-4 sm:px-6 py-4 sm:py-5 hover:no-underline hover:bg-neutral-50 transition-colors duration-150 gap-3 sm:gap-4">
                <div className="flex items-start space-x-3 sm:space-x-4 flex-1 text-left">
                  {/* Icon */}
                  <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-brand-100 to-accent-100 rounded-lg sm:rounded-xl flex items-center justify-center">
                    <Icon className="w-4 h-4 sm:w-5 sm:h-5 text-brand-600" />
                  </div>
                  {/* Question */}
                  <h3 className="text-sm sm:text-base lg:text-lg font-semibold text-primary-900 pr-2">
                    {item.question}
                  </h3>
                </div>
              </AccordionTrigger>

              <AccordionContent className="px-4 sm:px-6 pt-2 pb-4 sm:pb-5 pl-16 sm:pl-20 lg:pl-24">
                <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                  {item.answer}
                </p>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>

      {/* Bottom CTA */}
      <div className="text-center pt-4 sm:pt-6">
        <p className="text-sm sm:text-base text-primary-600">
          {t('faq.contactUs')}{' '}
          <a
            href="mailto:support@healthlingo.de"
            className="text-brand-600 hover:text-brand-700 font-medium underline underline-offset-2"
          >
            {t('faq.contactLink')}
          </a>
        </p>
      </div>
    </div>
  );
};

export default FAQ;
