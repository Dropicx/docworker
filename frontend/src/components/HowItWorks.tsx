import { useTranslation } from 'react-i18next';
import {
  Upload,
  Sparkles,
  FileCheck,
  Star,
  Smartphone,
  Lightbulb,
  Sun,
  Square,
  AlertCircle,
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

  const qualityTiers = [
    {
      level: 'best',
      stars: 3,
      color: 'from-amber-400 to-amber-500',
      bgColor: 'bg-amber-50',
      borderColor: 'border-amber-200',
      icon: '📄',
    },
    {
      level: 'great',
      stars: 2,
      color: 'from-brand-400 to-brand-500',
      bgColor: 'bg-brand-50',
      borderColor: 'border-brand-200',
      icon: '📱',
    },
    {
      level: 'good',
      stars: 1,
      color: 'from-accent-400 to-accent-500',
      bgColor: 'bg-accent-50',
      borderColor: 'border-accent-200',
      icon: '📸',
    },
  ];

  const proTips = [
    { icon: Lightbulb, key: 'pdf' },
    { icon: Smartphone, key: 'scanner' },
    { icon: Sun, key: 'light' },
    { icon: Square, key: 'flat' },
    { icon: AlertCircle, key: 'privacy' },
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
          {/* Desktop connecting line */}
          <div
            className="hidden lg:block absolute top-12 left-1/2 -translate-x-1/2 w-2/3 h-0.5 bg-gradient-to-r from-brand-200 via-brand-300 to-brand-200"
            aria-hidden="true"
          />

          {/* Steps Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
            {steps.map((step, index) => (
              <div key={step.number} className="relative">
                {/* Mobile connecting line (between cards) */}
                {index < steps.length - 1 && (
                  <div
                    className="lg:hidden absolute left-1/2 -translate-x-1/2 top-full h-6 w-0.5 bg-gradient-to-b from-brand-300 to-brand-200"
                    aria-hidden="true"
                  />
                )}

                {/* Step Card */}
                <Card className="text-center h-full hover:shadow-medium transition-all duration-300 border-t-2 border-t-brand-400">
                  <CardContent className="pt-6 pb-6 px-4 sm:px-6">
                    {/* Number Circle */}
                    <div className="relative inline-flex items-center justify-center mb-4">
                      <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center text-white shadow-soft">
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

      {/* Part B: Quality Tiers Card */}
      <div className="mb-10 sm:mb-14 lg:mb-16">
        <Card className="overflow-hidden border-t-2 border-t-accent-500">
          <CardContent className="p-4 sm:p-6 lg:p-8">
            <h3 className="text-xl sm:text-2xl font-bold text-primary-900 mb-6 text-center">
              {t('howItWorks.bestResults.title')}
            </h3>

            <div className="space-y-4">
              {qualityTiers.map((tier) => (
                <div
                  key={tier.level}
                  className={`rounded-xl border ${tier.borderColor} ${tier.bgColor} p-4 sm:p-5 transition-all duration-200 hover:shadow-soft`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start gap-3 sm:gap-4">
                    {/* Icon and Stars */}
                    <div className="flex items-center gap-3 sm:flex-col sm:items-center sm:w-20">
                      <span className="text-2xl sm:text-3xl" role="img" aria-hidden="true">
                        {tier.icon}
                      </span>
                      <div className="flex gap-0.5">
                        {[...Array(3)].map((_, i) => (
                          <Star
                            key={i}
                            className={`w-4 h-4 ${
                              i < tier.stars
                                ? 'text-amber-400 fill-amber-400'
                                : 'text-neutral-300'
                            }`}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className={`text-xs font-semibold uppercase tracking-wide bg-gradient-to-r ${tier.color} bg-clip-text text-transparent`}
                        >
                          {t(`howItWorks.bestResults.tiers.${tier.level}.label`)}
                        </span>
                      </div>
                      <h4 className="text-base sm:text-lg font-semibold text-primary-900 mb-1">
                        {t(`howItWorks.bestResults.tiers.${tier.level}.title`)}
                      </h4>
                      <p className="text-sm text-primary-600 mb-2">
                        {t(`howItWorks.bestResults.tiers.${tier.level}.description`)}
                      </p>

                      {/* Tips for 'good' tier */}
                      {tier.level === 'good' && (
                        <ul className="text-sm text-primary-600 space-y-1 mt-2">
                          {(
                            t(`howItWorks.bestResults.tiers.good.tips`, {
                              returnObjects: true,
                            }) as string[]
                          ).map((tip, i) => (
                            <li key={i} className="flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-accent-400 flex-shrink-0" />
                              {tip}
                            </li>
                          ))}
                        </ul>
                      )}

                      {/* Result badge */}
                      {tier.level !== 'good' && (
                        <p className="text-sm text-primary-500 italic">
                          → {t(`howItWorks.bestResults.tiers.${tier.level}.result`)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Part C: Pro Tips */}
      <div>
        <h3 className="text-xl sm:text-2xl font-bold text-primary-900 mb-4 sm:mb-6 text-center">
          {t('howItWorks.proTips.title')}
        </h3>

        <div className="flex flex-wrap justify-center gap-2 sm:gap-3">
          {proTips.map((tip) => (
            <div
              key={tip.key}
              className="inline-flex items-center gap-2 px-3 py-2 sm:px-4 sm:py-2.5 rounded-full bg-white border border-neutral-200 shadow-sm hover:shadow-soft hover:border-brand-200 transition-all duration-200"
            >
              <tip.icon className="w-4 h-4 text-brand-500 flex-shrink-0" />
              <span className="text-xs sm:text-sm text-primary-700">
                {t(`howItWorks.proTips.tips.${tip.key}`)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
