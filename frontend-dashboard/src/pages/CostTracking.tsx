import React, { useEffect, useState, useMemo } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';

interface CostEntry {
  source: string;
  run_id: string;
  cost_usd: number;
  updated_at: string;
}

interface CostSummary {
  totalCost: number;
  bySource: Record<string, number>;
  byRun: CostEntry[];
  averageCost: number;
  dailyCosts: Record<string, number>;
  sourceAverages: Record<string, number>;
}

const CostTracking: React.FC = () => {
  const [costs, setCosts] = useState<CostEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');

  useEffect(() => {
    const loadCosts = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/costs');
        if (!resp.ok) throw new Error(`Failed to load costs: ${resp.status}`);
        const result = await resp.json();
        const data: CostEntry[] = result.costs || [];
        
        // Fallback to mock data if API returns empty
        if (data.length === 0) {
        const mockData: CostEntry[] = [
          { source: 'alfabeta', run_id: 'run_2024_001', cost_usd: 12.45, updated_at: '2024-05-01T10:02:00Z' },
          { source: 'alfabeta', run_id: 'run_2024_002', cost_usd: 11.89, updated_at: '2024-05-02T10:02:00Z' },
          { source: 'quebec', run_id: 'run_2024_003', cost_usd: 8.23, updated_at: '2024-05-01T11:00:00Z' },
          { source: 'lafa', run_id: 'run_2024_004', cost_usd: 15.67, updated_at: '2024-05-01T11:30:00Z' },
          { source: 'alfabeta', run_id: 'run_2024_005', cost_usd: 13.12, updated_at: '2024-05-03T10:02:00Z' },
        ];
          setCosts(mockData);
        } else {
          setCosts(data);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to load costs', err);
        setError('Failed to load cost data');
      } finally {
        setLoading(false);
      }
    };

    loadCosts();
  }, []);

  const summary: CostSummary = useMemo(() => {
    const filtered = costs.filter(cost => {
      if (timeRange === 'all') return true;
      const costDate = new Date(cost.updated_at);
      const now = new Date();
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      return (now.getTime() - costDate.getTime()) / (1000 * 60 * 60 * 24) <= days;
    });

    const totalCost = filtered.reduce((sum, c) => sum + c.cost_usd, 0);
    const bySource: Record<string, number> = {};
    filtered.forEach(c => {
      bySource[c.source] = (bySource[c.source] || 0) + c.cost_usd;
    });

    // Calculate cost trends (daily aggregation)
    const dailyCosts: Record<string, number> = {};
    filtered.forEach(c => {
      const date = new Date(c.updated_at).toISOString().split('T')[0];
      dailyCosts[date] = (dailyCosts[date] || 0) + c.cost_usd;
    });

    // Calculate cost per source averages
    const sourceAverages: Record<string, number> = {};
    Object.keys(bySource).forEach(source => {
      const sourceRuns = filtered.filter(c => c.source === source);
      sourceAverages[source] = sourceRuns.length > 0 ? bySource[source] / sourceRuns.length : 0;
    });

    return {
      totalCost,
      bySource,
      byRun: filtered.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()),
      averageCost: filtered.length > 0 ? totalCost / filtered.length : 0,
      dailyCosts,
      sourceAverages,
    };
  }, [costs, timeRange]);

  if (loading && costs.length === 0) {
    return <LoadingSpinner message="Loading cost data..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
            Cost Tracking
          </h1>
          <p className="text-gray-600" style={{ margin: 0 }}>
            Monitor and analyze scraper execution costs
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {(['7d', '30d', '90d', 'all'] as const).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`btn btn-sm ${timeRange === range ? 'btn-primary' : 'btn-secondary'}`}
            >
              {range === 'all' ? 'All Time' : range}
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

      {/* Summary Cards */}
      <div className="metrics-grid" style={{ marginBottom: '2rem' }}>
        <div className="metric-card">
          <div className="metric-label">Total Cost</div>
          <div className="metric-value" style={{ color: 'var(--color-primary)' }}>
            ${summary.totalCost.toFixed(2)}
          </div>
          <div className="metric-change">
            <span>{summary.byRun.length} runs</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Average per Run</div>
          <div className="metric-value">${summary.averageCost.toFixed(2)}</div>
          <div className="metric-change">
            <span>Per execution</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Sources Tracked</div>
          <div className="metric-value">{Object.keys(summary.bySource).length}</div>
          <div className="metric-change">
            <span>Active sources</span>
          </div>
        </div>
      </div>

      {/* Cost Trends Chart */}
      {Object.keys(summary.dailyCosts).length > 0 && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Cost Trends</h2>
          <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', gap: '0.5rem', padding: '1rem 0' }}>
            {Object.entries(summary.dailyCosts)
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([date, cost]) => {
                const maxCost = Math.max(...Object.values(summary.dailyCosts));
                const height = maxCost > 0 ? (cost / maxCost) * 100 : 0;
                return (
                  <div key={date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div
                      style={{
                        width: '100%',
                        height: `${height}%`,
                        minHeight: cost > 0 ? '4px' : '0',
                        background: 'var(--color-primary)',
                        borderRadius: '4px 4px 0 0',
                        marginBottom: '0.5rem',
                      }}
                      title={`${date}: $${cost.toFixed(2)}`}
                    />
                    <div className="text-xs text-gray-500" style={{ transform: 'rotate(-45deg)', whiteSpace: 'nowrap' }}>
                      {new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Cost by Source */}
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Cost by Source</h2>
          {Object.keys(summary.bySource).length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {Object.entries(summary.bySource)
                .sort(([, a], [, b]) => b - a)
                .map(([source, cost]) => {
                  const percentage = summary.totalCost > 0 ? (cost / summary.totalCost) * 100 : 0;
                  const avgCost = summary.sourceAverages[source] || 0;
                  return (
                    <div key={source}>
                      <div className="flex-between mb-1">
                        <span className="text-sm" style={{ fontWeight: 600 }}>{source}</span>
                        <div style={{ textAlign: 'right' }}>
                          <span className="text-sm" style={{ fontWeight: 600 }}>${cost.toFixed(2)}</span>
                          <div className="text-xs text-gray-500">Avg: ${avgCost.toFixed(2)}/run</div>
                        </div>
                      </div>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-500" style={{ marginTop: '0.25rem' }}>
                        {percentage.toFixed(1)}% of total
                      </div>
                    </div>
                  );
                })}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No cost data available</p>
          )}
        </div>

        {/* Recent Costs */}
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '1.5rem' }}>Recent Costs</h2>
          {summary.byRun.length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Run ID</th>
                    <th>Cost</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.byRun.slice(0, 10).map((entry) => (
                    <tr key={`${entry.source}-${entry.run_id}`}>
                      <td>
                        <span className="badge">{entry.source}</span>
                      </td>
                      <td className="font-mono text-sm">{entry.run_id}</td>
                      <td style={{ fontWeight: 600 }}>${entry.cost_usd.toFixed(2)}</td>
                      <td className="text-sm">
                        {new Date(entry.updated_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No cost data available</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CostTracking;

