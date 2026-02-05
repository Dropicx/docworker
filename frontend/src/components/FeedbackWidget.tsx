/**
 * FeedbackWidget Component (Issue #47)
 *
 * A GDPR-compliant feedback widget with 5-star ratings,
 * optional detailed ratings, and explicit consent checkbox.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Star, ChevronDown, ChevronUp, Send, CheckCircle, MessageSquare } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { feedbackApi } from '../services/feedbackApi';
import type { DetailedRatings, FeedbackSubmission } from '../types/feedback';

interface FeedbackWidgetProps {
  processingId: string;
  onFeedbackSubmitted?: () => void;
}

interface StarRatingProps {
  value: number;
  onChange: (value: number) => void;
  label: string;
  required?: boolean;
  size?: 'sm' | 'md';
}

const StarRating: React.FC<StarRatingProps> = ({
  value,
  onChange,
  label,
  required = false,
  size = 'md',
}) => {
  const { t } = useTranslation();
  const [hovered, setHovered] = useState<number>(0);
  const starSize = size === 'sm' ? 'w-5 h-5' : 'w-7 h-7';

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-primary-700 font-medium">
        {label}
        {required && <span className="text-error-500 ml-1">*</span>}
      </span>
      <div className="flex space-x-1">
        {[1, 2, 3, 4, 5].map(star => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            onMouseEnter={() => setHovered(star)}
            onMouseLeave={() => setHovered(0)}
            className="focus:outline-none focus:ring-2 focus:ring-brand-500 rounded-sm transition-transform hover:scale-110"
            aria-label={t('feedback.starLabel', { count: star })}
          >
            <Star
              className={`${starSize} transition-colors duration-150 ${
                star <= (hovered || value)
                  ? 'fill-warning-400 text-warning-400'
                  : 'fill-none text-neutral-300 hover:text-neutral-400'
              }`}
            />
          </button>
        ))}
      </div>
    </div>
  );
};

const FeedbackWidget: React.FC<FeedbackWidgetProps> = ({ processingId, onFeedbackSubmitted }) => {
  const { t } = useTranslation();

  // State
  const [overallRating, setOverallRating] = useState<number>(0);
  const [showDetails, setShowDetails] = useState<boolean>(false);
  const [detailedRatings, setDetailedRatings] = useState<DetailedRatings>({});
  const [comment, setComment] = useState<string>('');
  const [consentGiven, setConsentGiven] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSubmitted, setIsSubmitted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [alreadySubmitted, setAlreadySubmitted] = useState<boolean>(false);

  // Check if feedback already exists on mount
  useEffect(() => {
    const checkExisting = async () => {
      try {
        const exists = await feedbackApi.checkFeedbackExists(processingId);
        if (exists) {
          setAlreadySubmitted(true);
          setIsSubmitted(true);
        }
      } catch {
        // Ignore errors - assume feedback doesn't exist
      }
    };
    checkExisting();
  }, [processingId]);

  // Cleanup on page leave (sendBeacon)
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (!isSubmitted && !alreadySubmitted) {
        feedbackApi.cleanupContent(processingId);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isSubmitted, alreadySubmitted, processingId]);

  // Handle detailed rating change
  const handleDetailedRating = useCallback((key: keyof DetailedRatings, value: number) => {
    setDetailedRatings(prev => ({ ...prev, [key]: value }));
  }, []);

  // Submit feedback
  const handleSubmit = async () => {
    if (overallRating === 0) {
      setError(t('feedback.ratingRequired'));
      return;
    }

    if (!consentGiven) {
      setError(t('feedback.consentRequired'));
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      // Filter out empty detailed ratings
      const filteredDetailedRatings: DetailedRatings = {};
      if (detailedRatings.clarity) filteredDetailedRatings.clarity = detailedRatings.clarity;
      if (detailedRatings.accuracy) filteredDetailedRatings.accuracy = detailedRatings.accuracy;
      if (detailedRatings.formatting)
        filteredDetailedRatings.formatting = detailedRatings.formatting;
      if (detailedRatings.speed) filteredDetailedRatings.speed = detailedRatings.speed;

      const submission: FeedbackSubmission = {
        processing_id: processingId,
        overall_rating: overallRating,
        detailed_ratings:
          Object.keys(filteredDetailedRatings).length > 0 ? filteredDetailedRatings : undefined,
        comment: comment.trim() || undefined,
        data_consent_given: consentGiven,
      };

      await feedbackApi.submitFeedback(submission);
      setIsSubmitted(true);
      // Note: Don't set alreadySubmitted here - that flag is only for feedback
      // that existed BEFORE this session. isSubmitted alone prevents cleanup.
      onFeedbackSubmitted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('feedback.submitError'));
    } finally {
      setIsSubmitting(false);
    }
  };

  // Already submitted state
  if (alreadySubmitted && isSubmitted) {
    return (
      <div className="glass-effect p-6 rounded-2xl border border-success-200/50 bg-gradient-to-br from-success-50/30 to-brand-50/30">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-success-400 to-success-500 rounded-xl flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-white" />
          </div>
          <div>
            <h4 className="font-semibold text-success-900">{t('feedback.alreadyReceived')}</h4>
            <p className="text-success-700 text-sm">
              {t('feedback.alreadyReceivedDescription')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Success state
  if (isSubmitted) {
    return (
      <div className="glass-effect p-6 rounded-2xl border border-success-200/50 bg-gradient-to-br from-success-50/30 to-brand-50/30 animate-fade-in">
        <div className="text-center space-y-3">
          <div className="w-16 h-16 bg-gradient-to-br from-success-400 to-success-500 rounded-2xl flex items-center justify-center mx-auto shadow-soft animate-bounce-once">
            <CheckCircle className="w-8 h-8 text-white" />
          </div>
          <h4 className="text-xl font-bold text-success-900">{t('feedback.thankYou')}</h4>
          <p className="text-success-700">{t('feedback.thankYouDescription')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card-elevated border-brand-200/50 bg-gradient-to-br from-brand-50/30 to-accent-50/30">
      <div className="card-body space-y-5">
        {/* Header */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-brand-500 to-accent-500 rounded-xl flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-primary-900">{t('feedback.title')}</h3>
            <p className="text-sm text-primary-600">{t('feedback.subtitle')}</p>
          </div>
        </div>

        {/* Overall Rating */}
        <div className="bg-white/50 rounded-xl p-4 border border-brand-100">
          <StarRating
            value={overallRating}
            onChange={setOverallRating}
            label={t('feedback.overallRating')}
            required
            size="md"
          />
        </div>

        {/* Detailed Ratings Toggle */}
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center justify-between w-full text-sm text-primary-600 hover:text-primary-800 transition-colors"
        >
          <span className="font-medium">{t('feedback.detailedOptional')}</span>
          {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {/* Detailed Ratings */}
        {showDetails && (
          <div className="space-y-3 animate-slide-down bg-white/30 rounded-xl p-4 border border-neutral-100">
            <StarRating
              value={detailedRatings.clarity || 0}
              onChange={v => handleDetailedRating('clarity', v)}
              label={t('feedback.clarity')}
              size="sm"
            />
            <StarRating
              value={detailedRatings.accuracy || 0}
              onChange={v => handleDetailedRating('accuracy', v)}
              label={t('feedback.accuracy')}
              size="sm"
            />
            <StarRating
              value={detailedRatings.formatting || 0}
              onChange={v => handleDetailedRating('formatting', v)}
              label={t('feedback.formatting')}
              size="sm"
            />
            <StarRating
              value={detailedRatings.speed || 0}
              onChange={v => handleDetailedRating('speed', v)}
              label={t('feedback.speed')}
              size="sm"
            />
          </div>
        )}

        {/* Comment */}
        <div>
          <label className="block text-sm font-medium text-primary-700 mb-2">
            {t('feedback.commentOptional')}
          </label>
          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder={t('feedback.commentPlaceholder')}
            className="w-full px-4 py-3 border border-neutral-200 rounded-xl focus:ring-2 focus:ring-brand-500 focus:border-brand-500 resize-none transition-all"
            rows={3}
            maxLength={1000}
          />
          <div className="text-xs text-primary-500 text-right mt-1">{comment.length}/1000</div>
        </div>

        {/* Consent Checkbox */}
        <div className="bg-brand-50/50 rounded-xl p-4 border border-brand-100">
          <label className="flex items-start space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consentGiven}
              onChange={e => setConsentGiven(e.target.checked)}
              className="mt-1 w-5 h-5 text-brand-600 border-neutral-300 rounded focus:ring-brand-500 cursor-pointer"
            />
            <span className="text-sm text-primary-700">
              {t('feedback.consent')}
              <span className="text-error-500 ml-1">*</span>
            </span>
          </label>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-error-50 border border-error-200 rounded-lg p-3 text-sm text-error-700">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || overallRating === 0 || !consentGiven}
          className="btn-primary w-full group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>{t('feedback.submitting')}</span>
            </>
          ) : (
            <>
              <Send className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              <span>{t('feedback.submit')}</span>
            </>
          )}
        </button>

        {/* Privacy Note */}
        <p className="text-xs text-primary-500 text-center">
          {t('feedback.privacyNote')}
        </p>
      </div>
    </div>
  );
};

export default FeedbackWidget;
