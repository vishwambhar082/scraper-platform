import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import RunListTable, { RunSummary } from '../components/RunListTable';
import VariantBenchmarkTable, { VariantBenchmark } from '../components/VariantBenchmarkTable';
import LoadingSpinner from '../components/LoadingSpinner';

const fallbackRuns: RunSummary[] = [
  { id: 'run_2024_001', source: 'alfabeta', status: 'success', startedAt: '2024-05-01T10:00Z', durationSeconds: 120, variantId: 'v1_baseline' },
  { id: 'run_2024_002', source: 'quebec', status: 'failed', startedAt: '2024-05-01T11:00Z', durationSeconds: 45, variantId: 'v2_aggressive_pcids' },
  { id: 'run_2024_003', source: 'lafa', status: 'running', startedAt: '2024-05-01T11:30Z', variantId: 'v1_baseline' },
];

const fallbackBenchmarks: VariantBenchmark[] = [
  { variantId: 'v1_baseline', totalRuns: 12, successRate: 0.92, dataCompleteness: 0.97, costPerRecord: 0.004, totalRecords: 3200 },
  { variantId: 'v2_aggressive_pcids', totalRuns: 8, successRate: 0.75, dataCompleteness: 0.83, costPerRecord: 0.003, totalRecords: 4100 },
];

const Dashboard: React.FC = () => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [benchmarks, setBenchmarks] = useState<VariantBenchmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sortedRuns = useMemo(
    () => [...runs].sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()),
    [runs]
  );

  const metrics = useMemo(() => {
    const totalRuns = runs.length;
    const successfulRuns = runs.filter((r) => r.status === 'success').length;
    const failedRuns = runs.filter((r) => r.status === 'failed').length;
    const runningRuns = runs.filter((r) => r.status === 'running').length;
    const successRate = totalRuns > 0 ? (successfulRuns / totalRuns) * 100 : 0;
    const avgDuration = runs
      .filter((r) => r.durationSeconds)
      .reduce((sum, r) => sum + (r.durationSeconds || 0), 0) / runs.filter((r) => r.durationSeconds).length || 0;

    return {
      totalRuns,
      successfulRuns,
      failedRuns,
      runningRuns,
      successRate,
      avgDuration,
    };
  }, [runs]);

  const upsertRun = useCallback((incoming: RunSummary) => {
    setRuns((current) => {
      const idx = current.findIndex((run) => run.id === incoming.id);
      if (idx === -1) return [incoming, ...current];
      const next = [...current];
      next[idx] = incoming;
      return next;
    });
  }, []);

  const removeRun = useCallback((id: string) => {
    setRuns((current) => current.filter((run) => run.id !== id));
  }, []);

  useEffect(() => {
    const loadRuns = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/runs?limit=100');
        if (!resp.ok) throw new Error(`Failed to load runs: ${resp.status}`);
        const data: RunSummary[] = await resp.json();
        setRuns(data);
        setError(null);
      } catch (err) {
        console.warn('Falling back to mock run list', err);
        setRuns(fallbackRuns);
        setError('Using fallback data');
      } finally {
        setLoading(false);
      }
    };

    loadRuns();

    if (typeof EventSource === 'undefined') {
      console.warn('EventSource is unavailable; skipping live run updates');
      return;
    }

    const eventSource = new EventSource('/api/runs/stream');

    const handleRunUpdate = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data) as RunSummary;
        upsertRun(payload);
      } catch (err) {
        console.error('Failed to parse SSE event', err);
      }
    };

    eventSource.addEventListener('snapshot', (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as RunSummary[];
        setRuns(payload);
      } catch (err) {
        console.error('Failed to parse SSE snapshot', err);
      }
    });

    eventSource.addEventListener('created', (event) => handleRunUpdate(event as MessageEvent));
    eventSource.addEventListener('updated', (event) => handleRunUpdate(event as MessageEvent));
    eventSource.addEventListener('completed', (event) => handleRunUpdate(event as MessageEvent));
    eventSource.addEventListener('deleted', (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent).data) as { id: string };
        removeRun(payload.id);
      } catch (err) {
        console.error('Failed to parse SSE delete event', err);
      }
    });

    eventSource.onerror = (err) => {
      console.warn('Run stream disconnected; keeping last known data', err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [upsertRun, removeRun]);

  useEffect(() => {
    const loadBenchmarks = async () => {
      try {
        const resp = await fetch('/api/variants/benchmarks');
        if (!resp.ok) throw new Error(`Failed to load benchmarks: ${resp.status}`);
        const data: VariantBenchmark[] = await resp.json();
        setBenchmarks(data);
      } catch (err) {
        console.warn('Falling back to mock benchmark data', err);
        setBenchmarks(fallbackBenchmarks);
      }
    };

    loadBenchmarks();
  }, []);

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  if (loading && runs.length === 0) {
    return <LoadingSpinner message="Loading dashboard..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
          Dashboard
        </h1>
        <p className="text-gray-600" style={{ margin: 0 }}>
          Real-time monitoring of scraper runs and performance metrics
        </p>
        {error && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '0.5rem',
              color: 'var(--color-warning)',
              fontSize: '0.875rem',
            }}
          >
            ⚠️ {error}
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Runs</div>
          <div className="metric-value">{metrics.totalRuns}</div>
          <div className="metric-change">
            <span>All time</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Success Rate</div>
          <div className="metric-value" style={{ color: metrics.successRate >= 90 ? 'var(--color-success)' : metrics.successRate >= 70 ? 'var(--color-warning)' : 'var(--color-error)' }}>
            {metrics.successRate.toFixed(1)}%
          </div>
          <div className="progress-bar" style={{ marginTop: '0.5rem' }}>
            <div
              className={`progress-fill ${metrics.successRate >= 90 ? 'success' : metrics.successRate >= 70 ? 'warning' : 'error'}`}
              style={{ width: `${metrics.successRate}%` }}
            />
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Successful Runs</div>
          <div className="metric-value" style={{ color: 'var(--color-success)' }}>
            {metrics.successfulRuns}
          </div>
          <div className="metric-change positive">
            {metrics.totalRuns > 0 ? `${((metrics.successfulRuns / metrics.totalRuns) * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Failed Runs</div>
          <div className="metric-value" style={{ color: 'var(--color-error)' }}>
            {metrics.failedRuns}
          </div>
          <div className="metric-change negative">
            {metrics.totalRuns > 0 ? `${((metrics.failedRuns / metrics.totalRuns) * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Running Now</div>
          <div className="metric-value" style={{ color: 'var(--color-primary)' }}>
            {metrics.runningRuns}
          </div>
          <div className="metric-change">
            <span className="status-dot" style={{ background: 'var(--color-primary)' }} />
            Active
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Duration</div>
          <div className="metric-value">{formatDuration(metrics.avgDuration)}</div>
          <div className="metric-change">
            <span>Per run</span>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ marginTop: '2rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <Link to="/hub" className="btn btn-primary" style={{ textDecoration: 'none' }}>
            🎯 Analytics Hub
          </Link>
          <Link to="/runs" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            🔍 Inspect Runs
          </Link>
          <Link to="/flow" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            ⚡ Execution Flow
          </Link>
          <Link to="/sources" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            🏥 Source Health
          </Link>
          <Link to="/airflow/manage" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            🔄 Airflow
          </Link>
          <Link to="/deploy" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            🚀 Deploy Scraper
          </Link>
        </div>
      </div>

      {/* Main Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginTop: '2rem' }}>
        <RunListTable runs={sortedRuns} />
        <VariantBenchmarkTable benchmarks={benchmarks} />
      </div>

      {/* Recent Activity Summary */}
      <div className="card" style={{ marginTop: '2rem' }}>
        <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Recent Activity</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <div className="text-sm text-gray-500">Last 24h Runs</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '0.25rem' }}>
              {runs.filter(r => {
                const runDate = new Date(r.startedAt);
                const now = new Date();
                return (now.getTime() - runDate.getTime()) / (1000 * 60 * 60) <= 24;
              }).length}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Active Sources</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '0.25rem' }}>
              {new Set(runs.map(r => r.source)).size}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Total Variants</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '0.25rem' }}>
              {new Set(runs.map(r => r.variantId).filter(Boolean)).size}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Currently Running</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '0.25rem', color: 'var(--color-primary)' }}>
              {metrics.runningRuns}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
