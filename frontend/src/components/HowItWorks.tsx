import { useTranslation } from 'react-i18next';
import {
  Upload,
  Sparkles,
  FileCheck,
  FileText,
  Smartphone,
  Camera,
} from 'lucide-react';
import { Card, CardContent } from './ui/card';

const HowItWorks = () => {
  const { t } = useTranslation();

  const steps = [
    {
      number: 1,
      icon: Upload,
      titleKey: 'howItWorks.steps.1.title',
      descriptionKey: 'howItWorks.steps.1.description',
    },
    {
      number: 2,
      icon: Sparkles,
      titleKey: 'howItWorks.steps.2.title',
      descriptionKey: 'howItWorks.steps.2.description',
    },
    {
      number: 3,
      icon: FileCheck,
      titleKey: 'howItWorks.steps.3.title',
      descriptionKey: 'howItWorks.steps.3.description',
    },
  ];

  return (
    <section className="py-8 sm:py-12 lg:py-16" aria-labelledby="how-it-works-title">
      {/* Section Header */}
      <div className="text-center mb-8 sm:mb-12">
        <h2
          id="how-it-works-title"
          className="text-2xl sm:text-3xl lg:text-4xl font-bold text-primary-900 mb-3 sm:mb-4"
        >
          {t('howItWorks.title')}
        </h2>
        <p className="text-base sm:text-lg text-primary-600 max-w-2xl mx-auto">
          {t('howItWorks.subtitle')}
        </p>
      </div>

      {/* Part A: 3-Step Process Timeline */}
      <div className="mb-10 sm:mb-14 lg:mb-16">
        <div className="relative">
          {/* Steps Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
            {steps.map((step, index) => (
              <div key={step.number} className="relative">
                {/* Step Card */}
                <Card className="group text-center h-full hover:shadow-medium transition-all duration-300 border-t-2 border-t-brand-400">
                  <CardContent className="pt-6 pb-6 px-4 sm:px-6">
                    {/* Number Circle */}
                    <div className="relative inline-flex items-center justify-center mb-4">
                      <div
                        className={`w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center text-white shadow-soft transition-transform duration-300 ease-out group-hover:scale-110 ${step.number === 2 ? 'group-hover:animate-icon-glow' : ''}`}
                      >
                        <step.icon className="w-6 h-6 sm:w-7 sm:h-7" />
                      </div>
                      <div className="absolute -top-1 -right-1 w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-white border-2 border-brand-500 flex items-center justify-center">
                        <span className="text-xs sm:text-sm font-bold text-brand-600">
                          {step.number}
                        </span>
                      </div>
                    </div>

                    {/* Content */}
                    <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2">
                      {t(step.titleKey)}
                    </h3>
                    <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                      {t(step.descriptionKey)}
                    </p>
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

const qualityTiersData = [
  {
    level: 'best',
    Icon: FileText,
    borderColor: 'border-l-brand-500',
    iconBg: 'bg-brand-500',
  },
  {
    level: 'great',
    Icon: Smartphone,
    borderColor: 'border-l-primary-400',
    iconBg: 'bg-primary-500',
  },
  {
    level: 'good',
    Icon: Camera,
    borderColor: 'border-l-neutral-400',
    iconBg: 'bg-neutral-500',
  },
];

export const BestResultsSection = () => {
  const { t } = useTranslation();
  return (
    <div className="h-full flex flex-col lg:items-start">
      <h3 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-primary-900 mb-6 text-center lg:text-left w-full">
        {t('howItWorks.bestResults.title')}
      </h3>
      <div className="flex flex-col gap-4 sm:gap-5 flex-1 w-full">
        {qualityTiersData.map((tier) => (
          <Card
            key={tier.level}
            className="group text-center lg:text-left border-t-2 border-t-brand-500 hover:shadow-medium hover:-translate-y-1 transition-all duration-300 w-full"
          >
            <CardContent className="flex flex-row items-start gap-4 sm:gap-5 p-4 sm:p-5">
              <div
                className="flex-shrink-0 w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex items-center justify-center bg-gradient-to-br from-brand-500 to-brand-600 text-white shadow-soft transition-transform duration-300 ease-out group-hover:scale-110"
                aria-hidden
              >
                <tier.Icon className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wider text-primary-500 mb-1">
                  {t(`howItWorks.bestResults.tiers.${tier.level}.label`)}
                </p>
                <h3 className="text-lg sm:text-xl font-bold text-primary-900 mb-2 sm:mb-3">
                  {t(`howItWorks.bestResults.tiers.${tier.level}.title`)}
                </h3>
                <p className="text-sm sm:text-base text-primary-600 leading-relaxed">
                  {t(`howItWorks.bestResults.tiers.${tier.level}.description`)}
                </p>
                {tier.level !== 'good' && (
                  <p className="text-sm text-primary-600 mt-2 font-medium">
                    {t(`howItWorks.bestResults.tiers.${tier.level}.result`)}
                  </p>
                )}
                {tier.level === 'good' && (
                  <ul className="mt-3 space-y-1.5 text-sm text-primary-600 text-left">
                    {(
                      t(`howItWorks.bestResults.tiers.good.tips`, {
                        returnObjects: true,
                      }) as string[]
                    ).map((tip, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span className="w-1 h-1 rounded-full bg-neutral-400 flex-shrink-0" />
                        {tip}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default HowItWorks;
