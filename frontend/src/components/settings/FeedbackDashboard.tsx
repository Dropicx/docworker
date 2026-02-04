/**
 * FeedbackDashboard Component (Issue #47)
 *
 * Admin dashboard for viewing and analyzing user feedback.
 * Shows statistics, filterable list, and expandable feedback details.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  AlertCircle,
  RefreshCw,
  Star,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  MessageCircle,
  BarChart3,
  Filter,
  FileText,
  Eye,
  EyeOff,
  Brain,
  AlertTriangle,
  Lightbulb,
  Clock,
  Loader2,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { feedbackApi } from '../../services/feedbackApi';
import type {
  FeedbackEntry,
  FeedbackStats,
  FeedbackDetail,
  FeedbackListQuery,
  AIAnalysisStatus,
} from '../../types/feedback';

// Date range preset options
type DateRangePreset = 'today' | 'week' | 'month' | 'all';

const DATE_PRESETS: { value: DateRangePreset; label: string }[] = [
  { value: 'today', label: 'Heute' },
  { value: 'week', label: 'Diese Woche' },
  { value: 'month', label: 'Dieser Monat' },
  { value: 'all', label: 'Gesamtzeit' },
];

// Helper to get date range from preset
function getDateRange(preset: DateRangePreset): { start?: string; end?: string } {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  switch (preset) {
    case 'today':
      return { start: today.toISOString() };
    case 'week': {
      const weekAgo = new Date(today);
      weekAgo.setDate(weekAgo.getDate() - 7);
      return { start: weekAgo.toISOString() };
    }
    case 'month': {
      const monthAgo = new Date(today);
      monthAgo.setMonth(monthAgo.getMonth() - 1);
      return { start: monthAgo.toISOString() };
    }
    case 'all':
    default:
      return {};
  }
}

// Format date for display in Berlin timezone
function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Berlin',
    });
  } catch {
    return '-';
  }
}

// Truncate processing ID for display
function truncateId(id: string, maxLength = 12): string {
  if (id.length <= maxLength) return id;
  return `${id.substring(0, maxLength)}...`;
}

// Star Rating Display Component
const StarDisplay: React.FC<{ rating: number; size?: 'sm' | 'md' }> = ({ rating, size = 'md' }) => {
  const starSize = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';
  return (
    <div className="flex space-x-0.5">
      {[1, 2, 3, 4, 5].map(star => (
        <Star
          key={star}
          className={`${starSize} ${
            star <= rating ? 'fill-warning-400 text-warning-400' : 'fill-none text-neutral-300'
          }`}
        />
      ))}
    </div>
  );
};

// AI Analysis Status Badge Component
const AIAnalysisStatusBadge: React.FC<{ status: AIAnalysisStatus | null }> = ({ status }) => {
  if (!status) return null;

  const config: Record<
    AIAnalysisStatus,
    { label: string; className: string; icon: React.ReactNode }
  > = {
    PENDING: {
      label: 'Ausstehend',
      className: 'bg-primary-100 text-primary-700 border-primary-300',
      icon: <Clock className="w-3 h-3" />,
    },
    PROCESSING: {
      label: 'Analysiere...',
      className: 'bg-brand-100 text-brand-700 border-brand-300',
      icon: <Loader2 className="w-3 h-3 animate-spin" />,
    },
    COMPLETED: {
      label: 'Abgeschlossen',
      className: 'bg-success-100 text-success-700 border-success-300',
      icon: <CheckCircle className="w-3 h-3" />,
    },
    FAILED: {
      label: 'Fehlgeschlagen',
      className: 'bg-error-100 text-error-700 border-error-300',
      icon: <XCircle className="w-3 h-3" />,
    },
    SKIPPED: {
      label: 'Übersprungen',
      className: 'bg-neutral-100 text-neutral-600 border-neutral-300',
      icon: <XCircle className="w-3 h-3" />,
    },
  };

  const { label, className, icon } = config[status];

  return (
    <span
      className={`inline-flex items-center space-x-1 px-2 py-0.5 text-xs font-medium rounded-full border ${className}`}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
};

// Quality Score Display Component
const QualityScoreDisplay: React.FC<{ score: number }> = ({ score }) => {
  const getColor = (s: number) => {
    if (s >= 8) return 'text-success-600';
    if (s >= 5) return 'text-warning-600';
    return 'text-error-600';
  };

  const getBgColor = (s: number) => {
    if (s >= 8) return 'bg-success-100';
    if (s >= 5) return 'bg-warning-100';
    return 'bg-error-100';
  };

  return (
    <div className="flex items-center space-x-2">
      <span className={`text-2xl font-bold ${getColor(score)}`}>{score}</span>
      <span className="text-sm text-primary-500">/ 10</span>
      <div className="flex-1 h-2 bg-primary-100 rounded-full overflow-hidden ml-2">
        <div
          className={`h-full rounded-full ${getBgColor(score)}`}
          style={{ width: `${score * 10}%` }}
        />
      </div>
    </div>
  );
};

const FeedbackDashboard: React.FC = () => {
  const { tokens } = useAuth();

  // Data states
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [entries, setEntries] = useState<FeedbackEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);

  // UI states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datePreset, setDatePreset] = useState<DateRangePreset>('all');

  // Filter states
  const [ratingFilter, setRatingFilter] = useState<number | undefined>(undefined);
  const [consentFilter, setConsentFilter] = useState<boolean | undefined>(undefined);
  const [sortBy, setSortBy] = useState<'submitted_at' | 'overall_rating'>('submitted_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(0);

  // Detail states
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [feedbackDetail, setFeedbackDetail] = useState<FeedbackDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const [showAnalysisText, setShowAnalysisText] = useState(false);

  const ITEMS_PER_PAGE = 10;

  // Update token when auth changes
  useEffect(() => {
    if (tokens?.access_token) {
      feedbackApi.updateToken(tokens.access_token);
    }
  }, [tokens]);

  // Fetch stats data
  const fetchStats = useCallback(async () => {
    const { start } = getDateRange(datePreset);
    const statsData = await feedbackApi.getStats(start);
    setStats(statsData);
  }, [datePreset]);

  // Fetch feedback entries
  const fetchEntries = useCallback(async () => {
    const { start, end } = getDateRange(datePreset);
    const query: FeedbackListQuery = {
      skip: currentPage * ITEMS_PER_PAGE,
      limit: ITEMS_PER_PAGE,
      sort_by: sortBy,
      sort_order: sortOrder,
      start_date: start,
      end_date: end,
      rating_filter: ratingFilter,
      consent_filter: consentFilter,
    };

    const response = await feedbackApi.listFeedback(query);
    setEntries(response.entries);
    setTotalEntries(response.total);
  }, [datePreset, currentPage, sortBy, sortOrder, ratingFilter, consentFilter]);

  // Main data fetch
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await Promise.all([fetchStats(), fetchEntries()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten');
    } finally {
      setIsLoading(false);
    }
  }, [fetchStats, fetchEntries]);

  // Initial load and refetch on filter changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Fetch feedback detail when expanded
  const handleExpandFeedback = async (feedbackId: number) => {
    if (expandedId === feedbackId) {
      setExpandedId(null);
      setFeedbackDetail(null);
      setShowContent(false);
      setShowAnalysisText(false);
      return;
    }

    setExpandedId(feedbackId);
    setLoadingDetail(true);
    setShowContent(false);
    setShowAnalysisText(false);
    try {
      const detail = await feedbackApi.getFeedbackDetail(feedbackId);
      setFeedbackDetail(detail);
    } catch (err) {
      console.error('Failed to load feedback detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Handle sort toggle
  const handleSort = (field: 'submitted_at' | 'overall_rating') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setCurrentPage(0);
  };

  // Rating distribution bar width
  const getRatingBarWidth = (count: number): number => {
    if (!stats || stats.total_feedback === 0) return 0;
    return (count / stats.total_feedback) * 100;
  };

  // Loading state
  if (isLoading && !stats) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center space-y-4">
          <RefreshCw className="w-12 h-12 text-brand-600 animate-spin mx-auto" />
          <p className="text-primary-600">Lade Feedback-Statistiken...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-primary-900">Feedback-Dashboard</h3>
          <button
            onClick={fetchData}
            className="flex items-center space-x-2 px-4 py-2 text-sm bg-brand-100 hover:bg-brand-200 text-brand-700 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Aktualisieren</span>
          </button>
        </div>

        <div className="bg-error-50 border border-error-200 rounded-lg p-6">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-6 h-6 text-error-600 flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h4 className="text-lg font-semibold text-error-900">Fehler beim Laden</h4>
              <p className="text-sm text-error-700">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-primary-900">Feedback-Dashboard</h3>
            <p className="text-sm text-primary-600">Nutzerfeedback analysieren und verwalten</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Date Range Preset */}
          <select
            value={datePreset}
            onChange={e => {
              setDatePreset(e.target.value as DateRangePreset);
              setCurrentPage(0);
            }}
            className="px-3 py-2 text-sm border border-primary-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
          >
            {DATE_PRESETS.map(preset => (
              <option key={preset.value} value={preset.value}>
                {preset.label}
              </option>
            ))}
          </select>

          <button
            onClick={fetchData}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 text-sm bg-brand-100 hover:bg-brand-200 text-brand-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Aktualisieren</span>
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Feedback */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <MessageCircle className="w-5 h-5 text-brand-600" />
            <h4 className="font-semibold text-primary-900">Feedback gesamt</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {stats?.total_feedback || 0}
            </span>
          </div>
        </div>

        {/* Average Rating */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Star className="w-5 h-5 text-warning-500" />
            <h4 className="font-semibold text-primary-900">Durchschnitt</h4>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {stats?.average_overall_rating.toFixed(1) || '0.0'}
            </span>
            <StarDisplay rating={Math.round(stats?.average_overall_rating || 0)} size="sm" />
          </div>
        </div>

        {/* Consent Rate */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <CheckCircle className="w-5 h-5 text-success-600" />
            <h4 className="font-semibold text-primary-900">Zustimmungsrate</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {(stats?.consent_rate || 0).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* With Comments */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <MessageSquare className="w-5 h-5 text-primary-600" />
            <h4 className="font-semibold text-primary-900">Mit Kommentar</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {stats?.with_comments_count || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Rating Distribution & Detailed Ratings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rating Distribution */}
        <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-primary-200">
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-primary-900">Bewertungsverteilung</h4>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {[5, 4, 3, 2, 1].map(rating => {
              const count = stats?.rating_distribution[String(rating)] || 0;
              const percentage = getRatingBarWidth(count);
              return (
                <div key={rating} className="flex items-center space-x-3">
                  <div className="flex items-center space-x-1 w-20">
                    <span className="text-sm font-medium text-primary-900">{rating}</span>
                    <Star className="w-4 h-4 fill-warning-400 text-warning-400" />
                  </div>
                  <div className="flex-1 h-4 bg-primary-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-warning-400 rounded-full transition-all duration-300"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <span className="text-sm text-primary-600 w-12 text-right">{count}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Detailed Ratings Averages */}
        <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-primary-200">
            <div className="flex items-center space-x-2">
              <Star className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-primary-900">Detailbewertungen (Durchschnitt)</h4>
            </div>
          </div>
          <div className="p-4 space-y-4">
            {[
              { key: 'clarity', label: 'Verständlichkeit' },
              { key: 'accuracy', label: 'Genauigkeit' },
              { key: 'formatting', label: 'Formatierung' },
              { key: 'speed', label: 'Geschwindigkeit' },
            ].map(({ key, label }) => {
              const value =
                stats?.average_detailed_ratings[
                  key as keyof typeof stats.average_detailed_ratings
                ] || 0;
              return (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-primary-700">{label}</span>
                  <div className="flex items-center space-x-2">
                    <StarDisplay rating={Math.round(value)} size="sm" />
                    <span className="text-sm text-primary-600 w-8 text-right">
                      {value > 0 ? value.toFixed(1) : '-'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Feedback Entries Table */}
      <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-primary-200">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h4 className="font-semibold text-primary-900">Feedback-Einträge</h4>
              <p className="text-sm text-primary-600">{totalEntries} Einträge insgesamt</p>
            </div>

            {/* Filters */}
            <div className="flex items-center space-x-3">
              <Filter className="w-4 h-4 text-primary-500 flex-shrink-0" />
              <select
                value={ratingFilter || ''}
                onChange={e => {
                  setRatingFilter(e.target.value ? Number(e.target.value) : undefined);
                  setCurrentPage(0);
                }}
                className="pl-3 pr-8 py-2 text-sm border border-primary-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white cursor-pointer"
              >
                <option value="">Alle Bewertungen</option>
                {[5, 4, 3, 2, 1].map(r => (
                  <option key={r} value={r}>
                    {r} Stern{r !== 1 ? 'e' : ''}
                  </option>
                ))}
              </select>

              <select
                value={consentFilter === undefined ? '' : consentFilter ? 'true' : 'false'}
                onChange={e => {
                  if (e.target.value === '') {
                    setConsentFilter(undefined);
                  } else {
                    setConsentFilter(e.target.value === 'true');
                  }
                  setCurrentPage(0);
                }}
                className="pl-3 pr-8 py-2 text-sm border border-primary-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white cursor-pointer"
              >
                <option value="">Alle Zustimmungen</option>
                <option value="true">Mit Zustimmung</option>
                <option value="false">Ohne Zustimmung</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-primary-200">
            <thead className="bg-primary-50">
              <tr>
                <th className="w-8 px-4 py-3"></th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  ID
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase cursor-pointer hover:bg-primary-100"
                  onClick={() => handleSort('overall_rating')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Bewertung</span>
                    {sortBy === 'overall_rating' && (
                      <span className="text-brand-600">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  Kommentar
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  Zustimmung
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  KI-Analyse
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase cursor-pointer hover:bg-primary-100"
                  onClick={() => handleSort('submitted_at')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Datum</span>
                    {sortBy === 'submitted_at' && (
                      <span className="text-brand-600">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary-100">
              {entries.length > 0 ? (
                entries.map(entry => (
                  <React.Fragment key={entry.id}>
                    <tr
                      className="hover:bg-primary-50 cursor-pointer"
                      onClick={() => handleExpandFeedback(entry.id)}
                    >
                      <td className="px-4 py-3">
                        {expandedId === entry.id ? (
                          <ChevronUp className="w-4 h-4 text-primary-600" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-primary-400" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-primary-900">
                        {truncateId(entry.processing_id)}
                      </td>
                      <td className="px-4 py-3">
                        <StarDisplay rating={entry.overall_rating} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-sm text-primary-600">
                        {entry.comment ? (
                          <span className="flex items-center space-x-1">
                            <MessageSquare className="w-4 h-4 text-brand-500" />
                            <span className="truncate max-w-[150px]">{entry.comment}</span>
                          </span>
                        ) : (
                          <span className="text-primary-400">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {entry.data_consent_given ? (
                          <span className="flex items-center space-x-1 text-success-600">
                            <CheckCircle className="w-4 h-4" />
                            <span className="text-sm">Ja</span>
                          </span>
                        ) : (
                          <span className="flex items-center space-x-1 text-error-500">
                            <XCircle className="w-4 h-4" />
                            <span className="text-sm">Nein</span>
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {entry.ai_analysis_status ? (
                          <div className="flex items-center space-x-1">
                            <AIAnalysisStatusBadge status={entry.ai_analysis_status} />
                            {entry.ai_analysis_quality_score !== null &&
                              entry.ai_analysis_status === 'COMPLETED' && (
                                <span className="text-xs font-medium text-primary-600 ml-1">
                                  ({entry.ai_analysis_quality_score}/10)
                                </span>
                              )}
                          </div>
                        ) : (
                          <span className="text-primary-400 text-sm">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-primary-600">
                        {formatDate(entry.submitted_at)}
                      </td>
                    </tr>

                    {/* Expanded Detail */}
                    {expandedId === entry.id && (
                      <tr>
                        <td colSpan={7} className="px-4 py-4 bg-primary-50">
                          {loadingDetail ? (
                            <div className="flex items-center justify-center py-4">
                              <RefreshCw className="w-5 h-5 text-brand-600 animate-spin" />
                            </div>
                          ) : feedbackDetail ? (
                            <div className="space-y-4">
                              {/* Ratings */}
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {/* Overall & Detailed Ratings */}
                                <div className="bg-white p-4 rounded border border-primary-200">
                                  <h5 className="font-semibold text-primary-900 mb-3">
                                    Bewertungen
                                  </h5>
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                      <span className="text-sm text-primary-600">Gesamt</span>
                                      <StarDisplay
                                        rating={feedbackDetail.overall_rating}
                                        size="sm"
                                      />
                                    </div>
                                    {feedbackDetail.detailed_ratings && (
                                      <>
                                        {feedbackDetail.detailed_ratings.clarity && (
                                          <div className="flex items-center justify-between">
                                            <span className="text-sm text-primary-600">
                                              Verständlichkeit
                                            </span>
                                            <StarDisplay
                                              rating={feedbackDetail.detailed_ratings.clarity}
                                              size="sm"
                                            />
                                          </div>
                                        )}
                                        {feedbackDetail.detailed_ratings.accuracy && (
                                          <div className="flex items-center justify-between">
                                            <span className="text-sm text-primary-600">
                                              Genauigkeit
                                            </span>
                                            <StarDisplay
                                              rating={feedbackDetail.detailed_ratings.accuracy}
                                              size="sm"
                                            />
                                          </div>
                                        )}
                                        {feedbackDetail.detailed_ratings.formatting && (
                                          <div className="flex items-center justify-between">
                                            <span className="text-sm text-primary-600">
                                              Formatierung
                                            </span>
                                            <StarDisplay
                                              rating={feedbackDetail.detailed_ratings.formatting}
                                              size="sm"
                                            />
                                          </div>
                                        )}
                                        {feedbackDetail.detailed_ratings.speed && (
                                          <div className="flex items-center justify-between">
                                            <span className="text-sm text-primary-600">
                                              Geschwindigkeit
                                            </span>
                                            <StarDisplay
                                              rating={feedbackDetail.detailed_ratings.speed}
                                              size="sm"
                                            />
                                          </div>
                                        )}
                                      </>
                                    )}
                                  </div>
                                </div>

                                {/* Comment */}
                                <div className="bg-white p-4 rounded border border-primary-200">
                                  <h5 className="font-semibold text-primary-900 mb-3">Kommentar</h5>
                                  {feedbackDetail.comment ? (
                                    <p className="text-sm text-primary-700 whitespace-pre-wrap">
                                      {feedbackDetail.comment}
                                    </p>
                                  ) : (
                                    <p className="text-sm text-primary-400 italic">
                                      Kein Kommentar
                                    </p>
                                  )}
                                </div>
                              </div>

                              {/* Job Data (if consented) */}
                              {feedbackDetail.data_consent_given && feedbackDetail.job_data && (
                                <div className="bg-white p-4 rounded border border-primary-200">
                                  <div className="flex items-center justify-between mb-3">
                                    <h5 className="font-semibold text-primary-900 flex items-center space-x-2">
                                      <FileText className="w-4 h-4" />
                                      <span>Verknüpfte Verarbeitung</span>
                                    </h5>
                                    {feedbackDetail.job_data.content_available && (
                                      <button
                                        onClick={e => {
                                          e.stopPropagation();
                                          setShowContent(!showContent);
                                        }}
                                        className="flex items-center space-x-1 text-sm text-brand-600 hover:text-brand-700"
                                      >
                                        {showContent ? (
                                          <>
                                            <EyeOff className="w-4 h-4" />
                                            <span>Inhalt ausblenden</span>
                                          </>
                                        ) : (
                                          <>
                                            <Eye className="w-4 h-4" />
                                            <span>Inhalt anzeigen</span>
                                          </>
                                        )}
                                      </button>
                                    )}
                                  </div>

                                  {/* Job Metadata */}
                                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                                    <div>
                                      <div className="text-xs text-primary-500">Dateiname</div>
                                      <div className="text-sm font-medium text-primary-900 truncate">
                                        {feedbackDetail.job_data.filename || '-'}
                                      </div>
                                    </div>
                                    <div>
                                      <div className="text-xs text-primary-500">Dokumenttyp</div>
                                      <div className="text-sm font-medium text-primary-900">
                                        {feedbackDetail.job_data.document_type || '-'}
                                      </div>
                                    </div>
                                    <div>
                                      <div className="text-xs text-primary-500">Status</div>
                                      <div className="text-sm font-medium text-primary-900">
                                        {feedbackDetail.job_data.status || '-'}
                                      </div>
                                    </div>
                                    <div>
                                      <div className="text-xs text-primary-500">
                                        Verarbeitungszeit
                                      </div>
                                      <div className="text-sm font-medium text-primary-900">
                                        {feedbackDetail.job_data.processing_time_seconds
                                          ? `${feedbackDetail.job_data.processing_time_seconds.toFixed(1)}s`
                                          : '-'}
                                      </div>
                                    </div>
                                  </div>

                                  {/* Document Content (if showing) */}
                                  {showContent && feedbackDetail.job_data.content_available && (
                                    <div className="space-y-3 border-t border-primary-200 pt-4">
                                      {feedbackDetail.job_data.original_text && (
                                        <div>
                                          <div className="text-xs font-semibold text-primary-600 mb-1">
                                            Originaltext:
                                          </div>
                                          <div className="text-xs text-primary-700 bg-primary-50 p-3 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
                                            {feedbackDetail.job_data.original_text}
                                          </div>
                                        </div>
                                      )}
                                      {feedbackDetail.job_data.translated_text && (
                                        <div>
                                          <div className="text-xs font-semibold text-primary-600 mb-1">
                                            Übersetzter Text:
                                          </div>
                                          <div className="text-xs text-primary-700 bg-primary-50 p-3 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
                                            {feedbackDetail.job_data.translated_text}
                                          </div>
                                        </div>
                                      )}
                                      {feedbackDetail.job_data.language_translated_text && (
                                        <div>
                                          <div className="text-xs font-semibold text-primary-600 mb-1">
                                            Sprachübersetzung:
                                          </div>
                                          <div className="text-xs text-primary-700 bg-primary-50 p-3 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
                                            {feedbackDetail.job_data.language_translated_text}
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}

                                  {!feedbackDetail.job_data.content_available && (
                                    <p className="text-xs text-primary-500 italic">
                                      Dokumentinhalt wurde gelöscht (GDPR-Konformität)
                                    </p>
                                  )}
                                </div>
                              )}

                              {/* AI Quality Analysis Section */}
                              {feedbackDetail.data_consent_given &&
                                feedbackDetail.ai_analysis_status && (
                                  <div className="bg-white p-4 rounded border border-primary-200">
                                    <div className="flex items-center justify-between mb-3">
                                      <h5 className="font-semibold text-primary-900 flex items-center space-x-2">
                                        <Brain className="w-4 h-4 text-brand-600" />
                                        <span>KI-Qualitätsanalyse</span>
                                      </h5>
                                      <AIAnalysisStatusBadge
                                        status={feedbackDetail.ai_analysis_status}
                                      />
                                    </div>

                                    {/* Analysis Content based on status */}
                                    {feedbackDetail.ai_analysis_status === 'PROCESSING' && (
                                      <div className="flex items-center space-x-2 text-brand-600">
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        <span className="text-sm">
                                          Analyse wird durchgeführt...
                                        </span>
                                      </div>
                                    )}

                                    {feedbackDetail.ai_analysis_status === 'PENDING' && (
                                      <div className="flex items-center space-x-2 text-primary-500">
                                        <Clock className="w-4 h-4" />
                                        <span className="text-sm">
                                          Analyse wartet auf Ausführung
                                        </span>
                                      </div>
                                    )}

                                    {feedbackDetail.ai_analysis_status === 'FAILED' &&
                                      feedbackDetail.ai_analysis_error && (
                                        <div className="bg-error-50 border border-error-200 rounded p-3">
                                          <div className="flex items-start space-x-2">
                                            <AlertCircle className="w-4 h-4 text-error-600 flex-shrink-0 mt-0.5" />
                                            <div>
                                              <p className="text-sm font-medium text-error-700">
                                                Analyse fehlgeschlagen
                                              </p>
                                              <p className="text-xs text-error-600 mt-1">
                                                {feedbackDetail.ai_analysis_error}
                                              </p>
                                            </div>
                                          </div>
                                        </div>
                                      )}

                                    {feedbackDetail.ai_analysis_status === 'SKIPPED' && (
                                      <p className="text-sm text-primary-500">
                                        Analyse wurde übersprungen (Feature deaktiviert)
                                      </p>
                                    )}

                                    {feedbackDetail.ai_analysis_status === 'COMPLETED' &&
                                      feedbackDetail.ai_analysis_summary && (
                                        <div className="space-y-4">
                                          {/* Quality Score */}
                                          <div>
                                            <div className="text-xs font-semibold text-primary-600 mb-2">
                                              Qualitätsbewertung
                                            </div>
                                            <QualityScoreDisplay
                                              score={
                                                feedbackDetail.ai_analysis_summary
                                                  .overall_quality_score
                                              }
                                            />
                                          </div>

                                          {/* PII Issues */}
                                          {feedbackDetail.ai_analysis_summary.pii_issues.length >
                                            0 && (
                                            <div>
                                              <div className="text-xs font-semibold text-error-600 mb-2 flex items-center space-x-1">
                                                <AlertTriangle className="w-3 h-3" />
                                                <span>
                                                  PII-Probleme (
                                                  {
                                                    feedbackDetail.ai_analysis_summary.pii_issues
                                                      .length
                                                  }
                                                  )
                                                </span>
                                              </div>
                                              <ul className="space-y-1">
                                                {feedbackDetail.ai_analysis_summary.pii_issues.map(
                                                  (issue, idx) => (
                                                    <li
                                                      key={idx}
                                                      className="text-xs text-error-700 bg-error-50 p-2 rounded flex items-start space-x-2"
                                                    >
                                                      <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                                      <span>{issue}</span>
                                                    </li>
                                                  )
                                                )}
                                              </ul>
                                            </div>
                                          )}

                                          {/* Translation Issues */}
                                          {feedbackDetail.ai_analysis_summary.translation_issues
                                            .length > 0 && (
                                            <div>
                                              <div className="text-xs font-semibold text-warning-600 mb-2 flex items-center space-x-1">
                                                <AlertCircle className="w-3 h-3" />
                                                <span>
                                                  Übersetzungsprobleme (
                                                  {
                                                    feedbackDetail.ai_analysis_summary
                                                      .translation_issues.length
                                                  }
                                                  )
                                                </span>
                                              </div>
                                              <ul className="space-y-1">
                                                {feedbackDetail.ai_analysis_summary.translation_issues.map(
                                                  (issue, idx) => (
                                                    <li
                                                      key={idx}
                                                      className="text-xs text-warning-700 bg-warning-50 p-2 rounded flex items-start space-x-2"
                                                    >
                                                      <AlertCircle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                                      <span>{issue}</span>
                                                    </li>
                                                  )
                                                )}
                                              </ul>
                                            </div>
                                          )}

                                          {/* Recommendations */}
                                          {feedbackDetail.ai_analysis_summary.recommendations
                                            .length > 0 && (
                                            <div>
                                              <div className="text-xs font-semibold text-brand-600 mb-2 flex items-center space-x-1">
                                                <Lightbulb className="w-3 h-3" />
                                                <span>
                                                  Empfehlungen (
                                                  {
                                                    feedbackDetail.ai_analysis_summary
                                                      .recommendations.length
                                                  }
                                                  )
                                                </span>
                                              </div>
                                              <ul className="space-y-1">
                                                {feedbackDetail.ai_analysis_summary.recommendations.map(
                                                  (rec, idx) => (
                                                    <li
                                                      key={idx}
                                                      className="text-xs text-brand-700 bg-brand-50 p-2 rounded flex items-start space-x-2"
                                                    >
                                                      <Lightbulb className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                                      <span>{rec}</span>
                                                    </li>
                                                  )
                                                )}
                                              </ul>
                                            </div>
                                          )}

                                          {/* No issues found */}
                                          {feedbackDetail.ai_analysis_summary.pii_issues.length ===
                                            0 &&
                                            feedbackDetail.ai_analysis_summary.translation_issues
                                              .length === 0 && (
                                              <div className="text-sm text-success-600 flex items-center space-x-2">
                                                <CheckCircle className="w-4 h-4" />
                                                <span>Keine Probleme gefunden</span>
                                              </div>
                                            )}

                                          {/* Full Analysis Text (collapsible) */}
                                          {feedbackDetail.ai_analysis_text && (
                                            <div className="border-t border-primary-200 pt-3 mt-3">
                                              <button
                                                onClick={e => {
                                                  e.stopPropagation();
                                                  setShowAnalysisText(!showAnalysisText);
                                                }}
                                                className="flex items-center space-x-1 text-xs text-brand-600 hover:text-brand-700"
                                              >
                                                {showAnalysisText ? (
                                                  <>
                                                    <ChevronUp className="w-3 h-3" />
                                                    <span>Vollständige Analyse ausblenden</span>
                                                  </>
                                                ) : (
                                                  <>
                                                    <ChevronDown className="w-3 h-3" />
                                                    <span>Vollständige Analyse anzeigen</span>
                                                  </>
                                                )}
                                              </button>
                                              {showAnalysisText && (
                                                <div className="mt-2 text-xs text-primary-700 bg-primary-50 p-3 rounded max-h-60 overflow-y-auto whitespace-pre-wrap">
                                                  {feedbackDetail.ai_analysis_text}
                                                </div>
                                              )}
                                            </div>
                                          )}

                                          {/* Analysis timestamp */}
                                          {feedbackDetail.ai_analysis_completed_at && (
                                            <div className="text-xs text-primary-400 mt-2">
                                              Analysiert am:{' '}
                                              {formatDate(feedbackDetail.ai_analysis_completed_at)}
                                            </div>
                                          )}
                                        </div>
                                      )}
                                  </div>
                                )}

                              {!feedbackDetail.data_consent_given && (
                                <div className="bg-warning-50 border border-warning-200 rounded p-3 text-sm text-warning-700">
                                  Keine Zustimmung zur Datenverwendung - Dokumentinhalt nicht
                                  verfügbar
                                </div>
                              )}

                              {/* Full ID */}
                              <div className="text-xs text-primary-500">
                                <span className="font-medium">Vollständige ID:</span>{' '}
                                <span className="font-mono">{feedbackDetail.processing_id}</span>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-primary-500 text-center">
                              Details konnten nicht geladen werden
                            </p>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-primary-500">
                    <MessageSquare className="w-8 h-8 mx-auto mb-2 text-primary-300" />
                    <p>Keine Feedback-Einträge gefunden</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalEntries > ITEMS_PER_PAGE && (
          <div className="p-4 border-t border-primary-200 flex items-center justify-between">
            <div className="text-sm text-primary-600">
              Zeige {currentPage * ITEMS_PER_PAGE + 1}-
              {Math.min((currentPage + 1) * ITEMS_PER_PAGE, totalEntries)} von {totalEntries}
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                disabled={currentPage === 0}
                className="px-3 py-1 text-sm border border-primary-300 rounded hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Zurück
              </button>
              <button
                onClick={() => setCurrentPage(p => p + 1)}
                disabled={(currentPage + 1) * ITEMS_PER_PAGE >= totalEntries}
                className="px-3 py-1 text-sm border border-primary-300 rounded hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Weiter
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FeedbackDashboard;
