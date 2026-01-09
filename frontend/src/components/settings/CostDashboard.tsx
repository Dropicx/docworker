import React, { useState, useEffect, useCallback } from 'react';
import {
  DollarSign,
  AlertCircle,
  RefreshCw,
  TrendingUp,
  Cpu,
  FileText,
  ChevronDown,
  ChevronUp,
  Search,
  ArrowUpDown,
  Hash,
  Brain,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { costApi } from '../../services/costApi';
import type {
  CostOverview,
  CostBreakdown,
  ProcessingJobCost,
  ProcessingJobDetail,
  DateRangePreset,
  SortBy,
  SortOrder,
  FeedbackAnalysisCost,
} from '../../types/cost';

// Date range preset options
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

// Format currency for display
function formatCurrency(value: number): string {
  if (value >= 1) {
    return `$${value.toFixed(2)}`;
  }
  return `$${value.toFixed(4)}`;
}

// Format large numbers with K/M suffix
function formatNumber(value: number): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toLocaleString('de-DE');
}

// Format date for display
function formatDate(isoString: string): string {
  try {
    return new Date(isoString).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
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

const CostDashboard: React.FC = () => {
  const { tokens } = useAuth();

  // Data states
  const [overview, setOverview] = useState<CostOverview | null>(null);
  const [breakdown, setBreakdown] = useState<CostBreakdown | null>(null);
  const [feedbackCosts, setFeedbackCosts] = useState<FeedbackAnalysisCost | null>(null);
  const [jobs, setJobs] = useState<ProcessingJobCost[]>([]);
  const [jobsTotal, setJobsTotal] = useState(0);

  // UI states
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [datePreset, setDatePreset] = useState<DateRangePreset>('all');

  // Jobs table states
  const [sortBy, setSortBy] = useState<SortBy>('date');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(0);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<ProcessingJobDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const ITEMS_PER_PAGE = 10;

  // Update token when auth changes
  useEffect(() => {
    if (tokens?.access_token) {
      costApi.updateToken(tokens.access_token);
    }
  }, [tokens]);

  // Fetch overview, breakdown, and feedback costs data
  const fetchOverviewData = useCallback(async () => {
    const { start, end } = getDateRange(datePreset);
    const [overviewData, breakdownData, feedbackData] = await Promise.all([
      costApi.getOverview(start, end),
      costApi.getBreakdown(start, end),
      costApi.getFeedbackAnalysisCosts(start, end),
    ]);
    setOverview(overviewData);
    setBreakdown(breakdownData);
    setFeedbackCosts(feedbackData);
  }, [datePreset]);

  // Fetch jobs data
  const fetchJobsData = useCallback(async () => {
    const response = await costApi.getProcessingJobs({
      skip: currentPage * ITEMS_PER_PAGE,
      limit: ITEMS_PER_PAGE,
      sort_by: sortBy,
      sort_order: sortOrder,
      search: searchQuery || undefined,
    });
    setJobs(response.jobs);
    setJobsTotal(response.total);
  }, [currentPage, sortBy, sortOrder, searchQuery]);

  // Main data fetch
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await Promise.all([fetchOverviewData(), fetchJobsData()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden der Daten');
    } finally {
      setIsLoading(false);
    }
  }, [fetchOverviewData, fetchJobsData]);

  // Initial load and refetch on filter changes
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Fetch job detail when expanded
  const handleExpandJob = async (processingId: string) => {
    if (expandedJobId === processingId) {
      setExpandedJobId(null);
      setJobDetail(null);
      return;
    }

    setExpandedJobId(processingId);
    setLoadingDetail(true);
    try {
      const detail = await costApi.getProcessingJobDetail(processingId);
      setJobDetail(detail);
    } catch (err) {
      console.error('Failed to load job detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  // Handle sort toggle
  const handleSort = (field: SortBy) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setCurrentPage(0);
  };

  // Handle search
  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setCurrentPage(0);
  };

  // Calculate percentages for breakdown bars
  const getBreakdownPercentage = (value: number, total: number): number => {
    if (total === 0) return 0;
    return (value / total) * 100;
  };

  const totalModelCost = breakdown
    ? Object.values(breakdown.by_model).reduce((sum, m) => sum + m.cost_usd, 0)
    : 0;

  const totalStepCost = breakdown
    ? Object.values(breakdown.by_step).reduce((sum, s) => sum + s.cost_usd, 0)
    : 0;

  // Loading state
  if (isLoading && !overview) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center space-y-4">
          <RefreshCw className="w-12 h-12 text-brand-600 animate-spin mx-auto" />
          <p className="text-primary-600">Lade Kostenstatistiken...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-primary-900">Kostenstatistik</h3>
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
            <DollarSign className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-primary-900">Kostenstatistik</h3>
            <p className="text-sm text-primary-600">AI-Nutzung und Kosten pro Verarbeitung</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Date Range Preset */}
          <select
            value={datePreset}
            onChange={(e) => {
              setDatePreset(e.target.value as DateRangePreset);
              setCurrentPage(0);
            }}
            className="px-3 py-2 text-sm border border-primary-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 bg-white"
          >
            {DATE_PRESETS.map((preset) => (
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
        {/* Total Cost */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <DollarSign className="w-5 h-5 text-success-600" />
            <h4 className="font-semibold text-primary-900">Gesamtkosten</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {formatCurrency(overview?.total_cost_usd || 0)}
            </span>
          </div>
        </div>

        {/* Total Tokens */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Hash className="w-5 h-5 text-primary-600" />
            <h4 className="font-semibold text-primary-900">Tokens</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {formatNumber(overview?.total_tokens || 0)}
            </span>
          </div>
        </div>

        {/* Total API Calls */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Cpu className="w-5 h-5 text-primary-600" />
            <h4 className="font-semibold text-primary-900">API-Aufrufe</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {formatNumber(overview?.total_calls || 0)}
            </span>
          </div>
        </div>

        {/* Average Cost per Document */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="w-5 h-5 text-brand-600" />
            <h4 className="font-semibold text-primary-900">Ø pro Dokument</h4>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-bold text-primary-900">
              {formatCurrency(overview?.average_cost_per_document || 0)}
            </span>
          </div>
          <div className="text-xs text-primary-500 mt-2">
            {overview?.document_count || 0} Dokumente verarbeitet
          </div>
        </div>
      </div>

      {/* Feedback Analysis Costs */}
      <div className="bg-gradient-to-br from-brand-50 to-brand-100 border border-brand-200 rounded-lg p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Brain className="w-5 h-5 text-brand-600" />
          <h4 className="font-semibold text-brand-900">Feedback-Analyse (KI)</h4>
          <span className="text-xs bg-brand-200 text-brand-700 px-2 py-0.5 rounded-full">
            Self-Improving
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-brand-600 uppercase font-medium">Kosten</div>
            <div className="text-2xl font-bold text-brand-900">
              {formatCurrency(feedbackCosts?.total_cost_usd || 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-brand-600 uppercase font-medium">Analysen</div>
            <div className="text-2xl font-bold text-brand-900">
              {feedbackCosts?.total_calls || 0}
            </div>
          </div>
          <div>
            <div className="text-xs text-brand-600 uppercase font-medium">Tokens</div>
            <div className="text-lg font-semibold text-brand-700">
              {formatNumber(feedbackCosts?.total_tokens || 0)}
            </div>
          </div>
          <div>
            <div className="text-xs text-brand-600 uppercase font-medium">Ø pro Analyse</div>
            <div className="text-lg font-semibold text-brand-700">
              {formatCurrency(feedbackCosts?.average_cost_per_analysis || 0)}
            </div>
          </div>
        </div>
      </div>

      {/* Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Model */}
        <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-primary-200">
            <h4 className="font-semibold text-primary-900">Kosten nach Modell</h4>
          </div>
          <div className="p-4 space-y-3">
            {breakdown && Object.entries(breakdown.by_model).length > 0 ? (
              Object.entries(breakdown.by_model)
                .sort((a, b) => b[1].cost_usd - a[1].cost_usd)
                .map(([model, data]) => {
                  const percentage = getBreakdownPercentage(data.cost_usd, totalModelCost);
                  return (
                    <div key={model} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-primary-900 truncate max-w-[60%]">
                          {model}
                        </span>
                        <div className="flex items-center space-x-2">
                          <span className="text-primary-600">{formatCurrency(data.cost_usd)}</span>
                          <span className="text-xs text-primary-500">({percentage.toFixed(0)}%)</span>
                        </div>
                      </div>
                      <div className="h-2 bg-primary-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-brand-500 rounded-full transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-primary-500">
                        {data.calls.toLocaleString('de-DE')} Aufrufe · {formatNumber(data.tokens)} Tokens
                      </div>
                    </div>
                  );
                })
            ) : (
              <p className="text-sm text-primary-500 text-center py-4">Keine Daten vorhanden</p>
            )}
          </div>
        </div>

        {/* By Pipeline Step */}
        <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-primary-200">
            <h4 className="font-semibold text-primary-900">Kosten nach Pipeline-Schritt</h4>
          </div>
          <div className="p-4 space-y-3">
            {breakdown && Object.entries(breakdown.by_step).length > 0 ? (
              Object.entries(breakdown.by_step)
                .sort((a, b) => b[1].cost_usd - a[1].cost_usd)
                .map(([step, data]) => {
                  const percentage = getBreakdownPercentage(data.cost_usd, totalStepCost);
                  return (
                    <div key={step} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium text-primary-900">{step}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-primary-600">{formatCurrency(data.cost_usd)}</span>
                          <span className="text-xs text-primary-500">({percentage.toFixed(0)}%)</span>
                        </div>
                      </div>
                      <div className="h-2 bg-primary-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-success-500 rounded-full transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-primary-500">
                        {data.calls.toLocaleString('de-DE')} Aufrufe · {formatNumber(data.tokens)} Tokens
                      </div>
                    </div>
                  );
                })
            ) : (
              <p className="text-sm text-primary-500 text-center py-4">Keine Daten vorhanden</p>
            )}
          </div>
        </div>
      </div>

      {/* Processing Jobs Table */}
      <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-primary-200">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h4 className="font-semibold text-primary-900">Verarbeitungsvorgänge</h4>
              <p className="text-sm text-primary-600">
                {jobsTotal} Vorgänge insgesamt
              </p>
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="w-4 h-4 text-primary-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="ID suchen..."
                value={searchQuery}
                onChange={handleSearch}
                className="pl-9 pr-4 py-2 text-sm border border-primary-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 w-48"
              />
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
                <th className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase">
                  Typ
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase cursor-pointer hover:bg-primary-100"
                  onClick={() => handleSort('cost')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Kosten</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase cursor-pointer hover:bg-primary-100"
                  onClick={() => handleSort('tokens')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Tokens</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-primary-700 uppercase cursor-pointer hover:bg-primary-100"
                  onClick={() => handleSort('date')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Datum</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary-100">
              {jobs.length > 0 ? (
                jobs.map((job) => (
                  <React.Fragment key={job.processing_id}>
                    <tr
                      className="hover:bg-primary-50 cursor-pointer"
                      onClick={() => handleExpandJob(job.processing_id)}
                    >
                      <td className="px-4 py-3">
                        {expandedJobId === job.processing_id ? (
                          <ChevronUp className="w-4 h-4 text-primary-600" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-primary-400" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-primary-900">
                        {truncateId(job.processing_id)}
                      </td>
                      <td className="px-4 py-3 text-sm text-primary-600">
                        {job.document_type || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-primary-900">
                        {formatCurrency(job.total_cost_usd)}
                      </td>
                      <td className="px-4 py-3 text-sm text-primary-600">
                        {formatNumber(job.total_tokens)}
                      </td>
                      <td className="px-4 py-3 text-sm text-primary-600">
                        {formatDate(job.created_at)}
                      </td>
                    </tr>

                    {/* Expanded Detail */}
                    {expandedJobId === job.processing_id && (
                      <tr>
                        <td colSpan={6} className="px-4 py-4 bg-primary-50">
                          {loadingDetail ? (
                            <div className="flex items-center justify-center py-4">
                              <RefreshCw className="w-5 h-5 text-brand-600 animate-spin" />
                            </div>
                          ) : jobDetail ? (
                            <div className="space-y-4">
                              {/* Summary */}
                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <div className="bg-white p-3 rounded border border-primary-200">
                                  <div className="text-xs text-primary-500 mb-1">Gesamtkosten</div>
                                  <div className="font-semibold text-primary-900">
                                    {formatCurrency(jobDetail.summary.total_cost_usd)}
                                  </div>
                                </div>
                                <div className="bg-white p-3 rounded border border-primary-200">
                                  <div className="text-xs text-primary-500 mb-1">Tokens</div>
                                  <div className="font-semibold text-primary-900">
                                    {formatNumber(jobDetail.summary.total_tokens)}
                                  </div>
                                </div>
                                <div className="bg-white p-3 rounded border border-primary-200">
                                  <div className="text-xs text-primary-500 mb-1">API-Aufrufe</div>
                                  <div className="font-semibold text-primary-900">
                                    {jobDetail.summary.total_calls}
                                  </div>
                                </div>
                                <div className="bg-white p-3 rounded border border-primary-200">
                                  <div className="text-xs text-primary-500 mb-1">Ø pro Aufruf</div>
                                  <div className="font-semibold text-primary-900">
                                    {formatCurrency(jobDetail.summary.average_cost_per_call)}
                                  </div>
                                </div>
                              </div>

                              {/* Entries Table */}
                              <div className="bg-white rounded border border-primary-200 overflow-hidden">
                                <table className="min-w-full divide-y divide-primary-200">
                                  <thead className="bg-primary-100">
                                    <tr>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-primary-700">
                                        Schritt
                                      </th>
                                      <th className="px-3 py-2 text-left text-xs font-semibold text-primary-700">
                                        Modell
                                      </th>
                                      <th className="px-3 py-2 text-right text-xs font-semibold text-primary-700">
                                        Tokens
                                      </th>
                                      <th className="px-3 py-2 text-right text-xs font-semibold text-primary-700">
                                        Kosten
                                      </th>
                                      <th className="px-3 py-2 text-right text-xs font-semibold text-primary-700">
                                        Zeit
                                      </th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-primary-100">
                                    {jobDetail.entries.map((entry) => (
                                      <tr key={entry.id}>
                                        <td className="px-3 py-2 text-xs text-primary-900">
                                          {entry.step_name}
                                        </td>
                                        <td className="px-3 py-2 text-xs text-primary-600 truncate max-w-[150px]">
                                          {entry.model_name || '-'}
                                        </td>
                                        <td className="px-3 py-2 text-xs text-primary-600 text-right">
                                          {formatNumber(entry.total_tokens)}
                                        </td>
                                        <td className="px-3 py-2 text-xs font-medium text-primary-900 text-right">
                                          {formatCurrency(entry.total_cost_usd)}
                                        </td>
                                        <td className="px-3 py-2 text-xs text-primary-600 text-right">
                                          {entry.processing_time_seconds
                                            ? `${entry.processing_time_seconds.toFixed(1)}s`
                                            : '-'}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>

                              {/* Full ID */}
                              <div className="text-xs text-primary-500">
                                <span className="font-medium">Vollständige ID:</span>{' '}
                                <span className="font-mono">{job.processing_id}</span>
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
                  <td colSpan={6} className="px-4 py-8 text-center text-primary-500">
                    <FileText className="w-8 h-8 mx-auto mb-2 text-primary-300" />
                    <p>Keine Verarbeitungsvorgänge gefunden</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {jobsTotal > ITEMS_PER_PAGE && (
          <div className="p-4 border-t border-primary-200 flex items-center justify-between">
            <div className="text-sm text-primary-600">
              Zeige {currentPage * ITEMS_PER_PAGE + 1}-
              {Math.min((currentPage + 1) * ITEMS_PER_PAGE, jobsTotal)} von {jobsTotal}
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
                disabled={currentPage === 0}
                className="px-3 py-1 text-sm border border-primary-300 rounded hover:bg-primary-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Zurück
              </button>
              <button
                onClick={() => setCurrentPage((p) => p + 1)}
                disabled={(currentPage + 1) * ITEMS_PER_PAGE >= jobsTotal}
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

export default CostDashboard;
