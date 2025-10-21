import React, { useState, useEffect } from 'react';
import { Activity, AlertCircle, CheckCircle, RefreshCw, Server } from 'lucide-react';

interface WorkerStats {
  workers: {
    total: number;
    active: number;
    details: any;
  };
  tasks: {
    total: number;
    details: any;
  };
  queues: {
    high_priority: number;
    default: number;
    low_priority: number;
    maintenance: number;
  };
}

interface FlowerStatus {
  available: boolean;
  flower_url: string;
  workers?: any;
  worker_count?: number;
  error?: string;
}

const FlowerDashboard: React.FC = () => {
  const [flowerStatus, setFlowerStatus] = useState<FlowerStatus | null>(null);
  const [workerStats, setWorkerStats] = useState<WorkerStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchFlowerStatus = async () => {
    try {
      const response = await fetch('/api/monitoring/flower-status');
      const data = await response.json();
      setFlowerStatus(data);

      if (!data.available) {
        setError(data.error || 'Flower service is not available');
      } else {
        setError(null);
      }
    } catch (err) {
      setError('Failed to fetch Flower status');
      console.error('Error fetching Flower status:', err);
    }
  };

  const fetchWorkerStats = async () => {
    try {
      const response = await fetch('/api/monitoring/worker-stats');
      if (response.ok) {
        const data = await response.json();
        setWorkerStats(data);
      }
    } catch (err) {
      console.error('Error fetching worker stats:', err);
    }
  };

  const fetchData = async () => {
    setIsLoading(true);
    await Promise.all([fetchFlowerStatus(), fetchWorkerStats()]);
    setIsLoading(false);
  };

  useEffect(() => {
    fetchData();

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchData();
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const handleRefresh = () => {
    fetchData();
  };

  if (isLoading && !flowerStatus) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center space-y-4">
          <RefreshCw className="w-12 h-12 text-brand-600 animate-spin mx-auto" />
          <p className="text-primary-600">Lade Monitoring-Daten...</p>
        </div>
      </div>
    );
  }

  if (error || !flowerStatus?.available) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-primary-900">Worker Monitoring</h3>
          <button
            onClick={handleRefresh}
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
              <h4 className="text-lg font-semibold text-error-900">
                Flower Service nicht verfügbar
              </h4>
              <p className="text-sm text-error-700">
                {error || 'Der Flower Monitoring-Service ist derzeit nicht erreichbar.'}
              </p>
              <div className="mt-4 p-3 bg-error-100 rounded border border-error-200">
                <p className="text-xs font-mono text-error-800">
                  Flower URL: {flowerStatus?.flower_url || 'Nicht konfiguriert'}
                </p>
              </div>
              <p className="text-sm text-error-600 mt-2">
                Bitte stellen Sie sicher, dass der Flower Service läuft und über die angegebene URL
                erreichbar ist.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-primary-900">Worker Monitoring</h3>
            <p className="text-sm text-primary-600">Echtzeit-Überwachung der Celery Worker</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm text-primary-700">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="rounded border-primary-300 text-brand-600 focus:ring-brand-500"
            />
            <span>Auto-Refresh (5s)</span>
          </label>
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 text-sm bg-brand-100 hover:bg-brand-200 text-brand-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Aktualisieren</span>
          </button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Workers Status */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Server className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-primary-900">Workers</h4>
            </div>
            {workerStats && workerStats.workers.active > 0 ? (
              <CheckCircle className="w-5 h-5 text-success-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-error-600" />
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-primary-900">
                {workerStats?.workers.active || 0}
              </span>
              <span className="text-sm text-primary-600">
                / {workerStats?.workers.total || 0} aktiv
              </span>
            </div>
            <p className="text-xs text-primary-500">
              {workerStats?.workers.active === workerStats?.workers.total
                ? 'Alle Worker online'
                : 'Einige Worker offline'}
            </p>
          </div>
        </div>

        {/* Tasks Status */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-primary-900">Tasks</h4>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-primary-900">
                {workerStats?.tasks.total || 0}
              </span>
              <span className="text-sm text-primary-600">gesamt</span>
            </div>
            <p className="text-xs text-primary-500">Alle Zeit</p>
          </div>
        </div>

        {/* Queue Status */}
        <div className="bg-white border border-primary-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-primary-600" />
              <h4 className="font-semibold text-primary-900">Queues</h4>
            </div>
          </div>

          <div className="space-y-1 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-primary-600">High Priority:</span>
              <span className="font-mono text-primary-900">
                {workerStats?.queues.high_priority || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-primary-600">Default:</span>
              <span className="font-mono text-primary-900">
                {workerStats?.queues.default || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-primary-600">Low Priority:</span>
              <span className="font-mono text-primary-900">
                {workerStats?.queues.low_priority || 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-primary-600">Maintenance:</span>
              <span className="font-mono text-primary-900">
                {workerStats?.queues.maintenance || 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Full Flower Dashboard Link */}
      <div className="bg-white border border-primary-200 rounded-lg overflow-hidden">
        <div className="p-6">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-gradient-to-br from-brand-600 to-brand-700 rounded-lg flex items-center justify-center flex-shrink-0">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-primary-900 mb-2">Vollständiges Flower Dashboard</h4>
              <p className="text-sm text-primary-600 mb-4">
                Öffnen Sie das vollständige Flower Dashboard in einem neuen Tab für erweiterte Monitoring-Funktionen:
              </p>
              <ul className="text-sm text-primary-600 space-y-1 mb-4 ml-4">
                <li>• Echtzeit-Graphen und Metriken</li>
                <li>• Detaillierte Task-Historie</li>
                <li>• Worker-Pool-Verwaltung</li>
                <li>• Task-Revocation und Retry-Management</li>
                <li>• Queue-Statistiken und Monitoring</li>
              </ul>
              <a
                href="/api/monitoring/flower/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-brand-600 to-brand-700 hover:from-brand-700 hover:to-brand-800 text-white font-medium rounded-lg transition-all shadow-md hover:shadow-lg"
              >
                <Activity className="w-5 h-5" />
                <span>Flower Dashboard öffnen</span>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlowerDashboard;
