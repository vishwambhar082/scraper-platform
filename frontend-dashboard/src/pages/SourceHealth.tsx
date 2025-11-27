import React, { useEffect, useState } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import { Link } from 'react-router-dom';

interface SourceHealthData {
  source: string;
  status: string;
  lastRunAt?: string;
  lastSuccessAt?: string;
  consecutiveFailures: number;
  budgetExhausted: boolean;
  totalRuns?: number;
  successRate?: number;
  avgDuration?: number;
}

const SourceHealth: React.FC = () => {
  const [healthData, setHealthData] = useState<SourceHealthData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadHealthData = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/source-health');
        if (!resp.ok) throw new Error(`Failed to load health data: ${resp.status}`);
        const data: SourceHealthData[] = await resp.json();
        setHealthData(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load source health', err);
        setError('Failed to load source health data');
        // Fallback to mock data
        setHealthData([
          {
            source: 'alfabeta',
            status: 'healthy',
            lastRunAt: '2024-05-01T10:02:00Z',
            lastSuccessAt: '2024-05-01T10:02:00Z',
            consecutiveFailures: 0,
            budgetExhausted: false,
            totalRuns: 45,
            successRate: 0.95,
            avgDuration: 120,
          },
          {
            source: 'quebec',
            status: 'degraded',
            lastRunAt: '2024-05-01T11:00:00Z',
            lastSuccessAt: '2024-05-01T09:00:00Z',
            consecutiveFailures: 1,
            budgetExhausted: false,
            totalRuns: 32,
            successRate: 0.78,
            avgDuration: 95,
          },
          {
            source: 'lafa',
            status: 'healthy',
            lastRunAt: '2024-05-01T11:30:00Z',
            lastSuccessAt: '2024-05-01T11:30:00Z',
            consecutiveFailures: 0,
            budgetExhausted: false,
            totalRuns: 28,
            successRate: 0.89,
            avgDuration: 145,
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadHealthData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'var(--color-success)';
      case 'degraded':
        return 'var(--color-warning)';
      case 'unhealthy':
        return 'var(--color-error)';
      default:
        return 'var(--color-gray-500)';
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  if (loading && healthData.length === 0) {
    return <LoadingSpinner message="Loading source health data..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
          Source Health
        </h1>
        <p className="text-gray-600" style={{ margin: 0 }}>
          Monitor the health and performance of all scraper sources
        </p>
      </div>

      {error && (
        <div style={{
          marginBottom: '1.5rem',
          padding: '0.75rem',
          background: 'rgba(59, 130, 246, 0.1)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          borderRadius: '0.5rem',
          color: 'var(--color-warning)',
          fontSize: '0.875rem',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Summary Stats */}
      <div className="metrics-grid" style={{ marginBottom: '2rem' }}>
        <div className="metric-card">
          <div className="metric-label">Total Sources</div>
          <div className="metric-value">{healthData.length}</div>
          <div className="metric-change">
            <span>Active sources</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Healthy</div>
          <div className="metric-value" style={{ color: 'var(--color-success)' }}>
            {healthData.filter(h => h.status === 'healthy').length}
          </div>
          <div className="metric-change">
            <span>
              {healthData.length > 0
                ? `${((healthData.filter(h => h.status === 'healthy').length / healthData.length) * 100).toFixed(0)}%`
                : '0%'}
            </span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Degraded</div>
          <div className="metric-value" style={{ color: 'var(--color-warning)' }}>
            {healthData.filter(h => h.status === 'degraded').length}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Unhealthy</div>
          <div className="metric-value" style={{ color: 'var(--color-error)' }}>
            {healthData.filter(h => h.status === 'unhealthy').length}
          </div>
        </div>
      </div>

      {/* Health Table */}
      <div className="card">
        <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Source Details</h2>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Status</th>
                <th>Last Run</th>
                <th>Last Success</th>
                <th>Consecutive Failures</th>
                <th>Total Runs</th>
                <th>Success Rate</th>
                <th>Avg Duration</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {healthData.map((source) => (
                <tr key={source.source}>
                  <td>
                    <span className="badge" style={{ fontSize: '0.875rem' }}>
                      {source.source}
                    </span>
                  </td>
                  <td>
                    <span
                      className="status-tag"
                      style={{
                        background: `${getStatusColor(source.status)}20`,
                        color: getStatusColor(source.status),
                        borderColor: `${getStatusColor(source.status)}40`,
                      }}
                    >
                      <span
                        className="status-dot"
                        style={{ background: getStatusColor(source.status) }}
                      />
                      {source.status}
                    </span>
                  </td>
                  <td className="text-sm">
                    {source.lastRunAt
                      ? new Date(source.lastRunAt).toLocaleString()
                      : 'Never'}
                  </td>
                  <td className="text-sm">
                    {source.lastSuccessAt
                      ? new Date(source.lastSuccessAt).toLocaleString()
                      : 'Never'}
                  </td>
                  <td>
                    {source.consecutiveFailures > 0 ? (
                      <span style={{ color: 'var(--color-error)', fontWeight: 600 }}>
                        {source.consecutiveFailures}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--color-success)' }}>0</span>
                    )}
                  </td>
                  <td>{source.totalRuns ?? 'N/A'}</td>
                  <td>
                    {source.successRate !== undefined ? (
                      <div>
                        <div className="flex-between mb-1">
                          <span className="text-sm">{(source.successRate * 100).toFixed(1)}%</span>
                        </div>
                        <div className="progress-bar" style={{ height: '6px' }}>
                          <div
                            className={`progress-fill ${
                              source.successRate >= 0.9
                                ? 'success'
                                : source.successRate >= 0.7
                                ? 'warning'
                                : 'error'
                            }`}
                            style={{ width: `${source.successRate * 100}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      'N/A'
                    )}
                  </td>
                  <td className="text-sm">{formatDuration(source.avgDuration)}</td>
                  <td>
                    <Link
                      to={`/runs?source=${source.source}`}
                      className="btn btn-sm btn-secondary"
                      style={{ textDecoration: 'none' }}
                    >
                      View Runs
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SourceHealth;

