import React, { useEffect, useState, useMemo } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';

interface RunSummary {
  id: string;
  source: string;
  status: string;
  startedAt: string;
  durationSeconds?: number;
  variantId?: string;
}

interface AnalyticsData {
  totalRuns: number;
  successRate: number;
  avgDuration: number;
  bySource: Record<string, { total: number; success: number; avgDuration: number }>;
  byVariant: Record<string, { total: number; success: number; avgDuration: number }>;
  trends: Array<{ date: string; runs: number; success: number }>;
}

const PerformanceAnalytics: React.FC = () => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  useEffect(() => {
    const loadRuns = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/runs?limit=1000');
        if (!resp.ok) throw new Error(`Failed to load runs: ${resp.status}`);
        const data: RunSummary[] = await resp.json();
        setRuns(data);
        setError(null);
      } catch (err) {
        console.error('Failed to load runs', err);
        setError('Failed to load analytics data');
      } finally {
        setLoading(false);
      }
    };

    loadRuns();
  }, []);

  const analytics: AnalyticsData = useMemo(() => {
    const filtered = runs.filter(run => {
      const runDate = new Date(run.startedAt);
      const now = new Date();
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      return (now.getTime() - runDate.getTime()) / (1000 * 60 * 60 * 24) <= days;
    });

    const totalRuns = filtered.length;
    const successfulRuns = filtered.filter(r => r.status === 'success').length;
    const successRate = totalRuns > 0 ? successfulRuns / totalRuns : 0;
    const durations = filtered.filter(r => r.durationSeconds).map(r => r.durationSeconds!);
    const avgDuration = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;

    const bySource: Record<string, { total: number; success: number; avgDuration: number }> = {};
    const byVariant: Record<string, { total: number; success: number; avgDuration: number }> = {};

    filtered.forEach(run => {
      // By source
      if (!bySource[run.source]) {
        bySource[run.source] = { total: 0, success: 0, avgDuration: 0 };
      }
      bySource[run.source].total++;
      if (run.status === 'success') bySource[run.source].success++;
      if (run.durationSeconds) {
        bySource[run.source].avgDuration =
          (bySource[run.source].avgDuration * (bySource[run.source].total - 1) + run.durationSeconds) /
          bySource[run.source].total;
      }

      // By variant
      const variant = run.variantId || 'default';
      if (!byVariant[variant]) {
        byVariant[variant] = { total: 0, success: 0, avgDuration: 0 };
      }
      byVariant[variant].total++;
      if (run.status === 'success') byVariant[variant].success++;
      if (run.durationSeconds) {
        byVariant[variant].avgDuration =
          (byVariant[variant].avgDuration * (byVariant[variant].total - 1) + run.durationSeconds) /
          byVariant[variant].total;
      }
    });

    // Trends (group by date)
    const trendsMap = new Map<string, { runs: number; success: number }>();
    filtered.forEach(run => {
      const date = new Date(run.startedAt).toISOString().split('T')[0];
      const existing = trendsMap.get(date) || { runs: 0, success: 0 };
      existing.runs++;
      if (run.status === 'success') existing.success++;
      trendsMap.set(date, existing);
    });
    const trends = Array.from(trendsMap.entries())
      .map(([date, data]) => ({ date, ...data }))
      .sort((a, b) => a.date.localeCompare(b.date));

    return {
      totalRuns,
      successRate,
      avgDuration,
      bySource,
      byVariant,
      trends,
    };
  }, [runs, timeRange]);

  if (loading && runs.length === 0) {
    return <LoadingSpinner message="Loading analytics..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
            Performance Analytics
          </h1>
          <p className="text-gray-600" style={{ margin: 0 }}>
            Comprehensive performance metrics and trends
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {(['7d', '30d', '90d'] as const).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`btn btn-sm ${timeRange === range ? 'btn-primary' : 'btn-secondary'}`}
            >
              {range}
            </button>
          ))}
        </div>
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

      {/* Key Metrics */}
      <div className="metrics-grid" style={{ marginBottom: '2rem' }}>
        <div className="metric-card">
          <div className="metric-label">Total Runs</div>
          <div className="metric-value">{analytics.totalRuns}</div>
          <div className="metric-change">
            <span>Last {timeRange}</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Success Rate</div>
          <div
            className="metric-value"
            style={{
              color:
                analytics.successRate >= 0.9
                  ? 'var(--color-success)'
                  : analytics.successRate >= 0.7
                  ? 'var(--color-warning)'
                  : 'var(--color-error)',
            }}
          >
            {(analytics.successRate * 100).toFixed(1)}%
          </div>
          <div className="progress-bar" style={{ marginTop: '0.5rem' }}>
            <div
              className={`progress-fill ${
                analytics.successRate >= 0.9 ? 'success' : analytics.successRate >= 0.7 ? 'warning' : 'error'
              }`}
              style={{ width: `${analytics.successRate * 100}%` }}
            />
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Duration</div>
          <div className="metric-value">
            {analytics.avgDuration < 60
              ? `${Math.round(analytics.avgDuration)}s`
              : `${Math.floor(analytics.avgDuration / 60)}m ${Math.round(analytics.avgDuration % 60)}s`}
          </div>
          <div className="metric-change">
            <span>Per run</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Active Sources</div>
          <div className="metric-value">{Object.keys(analytics.bySource).length}</div>
          <div className="metric-change">
            <span>Sources tracked</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Performance by Source */}
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Performance by Source</h2>
          {Object.keys(analytics.bySource).length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Runs</th>
                    <th>Success Rate</th>
                    <th>Avg Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(analytics.bySource)
                    .sort(([, a], [, b]) => b.total - a.total)
                    .map(([source, data]) => (
                      <tr key={source}>
                        <td>
                          <span className="badge">{source}</span>
                        </td>
                        <td>{data.total}</td>
                        <td>
                          <div className="flex-between mb-1">
                            <span className="text-sm">
                              {data.total > 0 ? ((data.success / data.total) * 100).toFixed(1) : 0}%
                            </span>
                          </div>
                          <div className="progress-bar" style={{ height: '6px' }}>
                            <div
                              className={`progress-fill ${
                                data.success / data.total >= 0.9
                                  ? 'success'
                                  : data.success / data.total >= 0.7
                                  ? 'warning'
                                  : 'error'
                              }`}
                              style={{ width: `${(data.success / data.total) * 100}%` }}
                            />
                          </div>
                        </td>
                        <td className="text-sm">
                          {data.avgDuration < 60
                            ? `${Math.round(data.avgDuration)}s`
                            : `${Math.floor(data.avgDuration / 60)}m ${Math.round(data.avgDuration % 60)}s`}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No data available</p>
          )}
        </div>

        {/* Performance by Variant */}
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Performance by Variant</h2>
          {Object.keys(analytics.byVariant).length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Runs</th>
                    <th>Success Rate</th>
                    <th>Avg Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(analytics.byVariant)
                    .sort(([, a], [, b]) => b.total - a.total)
                    .map(([variant, data]) => (
                      <tr key={variant}>
                        <td>
                          <span className="badge" style={{ background: 'var(--color-primary)', color: 'white' }}>
                            {variant}
                          </span>
                        </td>
                        <td>{data.total}</td>
                        <td>
                          <div className="flex-between mb-1">
                            <span className="text-sm">
                              {data.total > 0 ? ((data.success / data.total) * 100).toFixed(1) : 0}%
                            </span>
                          </div>
                          <div className="progress-bar" style={{ height: '6px' }}>
                            <div
                              className={`progress-fill ${
                                data.success / data.total >= 0.9
                                  ? 'success'
                                  : data.success / data.total >= 0.7
                                  ? 'warning'
                                  : 'error'
                              }`}
                              style={{ width: `${(data.success / data.total) * 100}%` }}
                            />
                          </div>
                        </td>
                        <td className="text-sm">
                          {data.avgDuration < 60
                            ? `${Math.round(data.avgDuration)}s`
                            : `${Math.floor(data.avgDuration / 60)}m ${Math.round(data.avgDuration % 60)}s`}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No data available</p>
          )}
        </div>
      </div>

      {/* Trends */}
      <div className="card">
        <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Run Trends</h2>
        {analytics.trends.length > 0 ? (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Total Runs</th>
                  <th>Successful</th>
                  <th>Success Rate</th>
                </tr>
              </thead>
              <tbody>
                {analytics.trends.map((trend) => (
                  <tr key={trend.date}>
                    <td>{new Date(trend.date).toLocaleDateString()}</td>
                    <td>{trend.runs}</td>
                    <td style={{ color: 'var(--color-success)', fontWeight: 600 }}>{trend.success}</td>
                    <td>
                      <div className="flex-between mb-1">
                        <span className="text-sm">
                          {trend.runs > 0 ? ((trend.success / trend.runs) * 100).toFixed(1) : 0}%
                        </span>
                      </div>
                      <div className="progress-bar" style={{ height: '6px' }}>
                        <div
                          className={`progress-fill ${
                            trend.success / trend.runs >= 0.9
                              ? 'success'
                              : trend.success / trend.runs >= 0.7
                              ? 'warning'
                              : 'error'
                          }`}
                          style={{ width: `${(trend.success / trend.runs) * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No trend data available</p>
        )}
      </div>
    </div>
  );
};

export default PerformanceAnalytics;

