import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import RunListTable, { RunSummary } from '../components/RunListTable';
import RunDetailPanel, { RunDetail } from '../components/RunDetailPanel';
import LoadingSpinner from '../components/LoadingSpinner';

const fallbackRuns: RunSummary[] = [
  { id: 'run_2024_001', source: 'alfabeta', status: 'success', startedAt: '2024-05-01T10:00Z', durationSeconds: 120, variantId: 'v1_baseline' },
  { id: 'run_2024_002', source: 'quebec', status: 'failed', startedAt: '2024-05-01T11:00Z', durationSeconds: 45, variantId: 'v2_aggressive_pcids' },
  { id: 'run_2024_003', source: 'lafa', status: 'running', startedAt: '2024-05-01T11:30Z', variantId: 'v1_baseline' },
];

const fallbackDetails: Record<string, RunDetail> = {
  run_2024_001: {
    id: 'run_2024_001',
    source: 'alfabeta',
    status: 'success',
    startedAt: '2024-05-01T10:00Z',
    finishedAt: '2024-05-01T10:02Z',
    variantId: 'v1_baseline',
    stats: { products: 1200, invalid: 12, drift_events: 0 },
    steps: [
      { id: 'step1', name: 'company_index', status: 'success', startedAt: '2024-05-01T10:00Z', durationSeconds: 30 },
      { id: 'step2', name: 'product_index', status: 'success', startedAt: '2024-05-01T10:00:30Z', durationSeconds: 40 },
      { id: 'step3', name: 'extract_product', status: 'success', startedAt: '2024-05-01T10:01:10Z', durationSeconds: 50 },
    ],
    metadata: { version: '5.0.0', env: 'prod' },
  },
  run_2024_002: {
    id: 'run_2024_002',
    source: 'quebec',
    status: 'failed',
    startedAt: '2024-05-01T11:00Z',
    variantId: 'v2_aggressive_pcids',
    stats: { products: 0, invalid: 0, drift_events: 1 },
    steps: [
      { id: 'step1', name: 'company_index', status: 'failed', startedAt: '2024-05-01T11:00Z', durationSeconds: 45, error: 'Drift detected on listing page' },
    ],
    metadata: { error: 'Drift detected on listing page' },
    error: 'Drift detected on listing page',
  },
  run_2024_003: {
    id: 'run_2024_003',
    source: 'lafa',
    status: 'running',
    startedAt: '2024-05-01T11:30Z',
    variantId: 'v1_baseline',
    stats: { products: 200 },
    steps: [
      { id: 'step1', name: 'company_index', status: 'success', startedAt: '2024-05-01T11:30Z', durationSeconds: 20 },
      { id: 'step2', name: 'product_index', status: 'running', startedAt: '2024-05-01T11:30:20Z' },
    ],
    metadata: { note: 'still running' },
  },
};

const RunInspector: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get('run') || null);
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    setSearchParams({ run: id });
  }, [setSearchParams]);

  useEffect(() => {
    const loadRuns = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/runs?limit=100');
        if (!resp.ok) throw new Error(`Failed to load runs: ${resp.status}`);
        const data: RunSummary[] = await resp.json();
        setRuns(data);
        if (!selectedId && data.length > 0) {
          handleSelect(data[0].id);
        }
        setError(null);
      } catch (err) {
        console.warn('Falling back to mock run list', err);
        setRuns(fallbackRuns);
        if (!selectedId && fallbackRuns.length > 0) {
          handleSelect(fallbackRuns[0].id);
        }
        setError('Using fallback data');
      } finally {
        setLoading(false);
      }
    };

    loadRuns();
  }, [selectedId, handleSelect]);

  useEffect(() => {
    if (!selectedId) return;

    const loadDetail = async () => {
      try {
        setDetailLoading(true);
        const [detailResp, stepsResp] = await Promise.all([
          fetch(`/api/runs/${selectedId}`),
          fetch(`/api/steps/${selectedId}`),
        ]);

        if (!detailResp.ok) throw new Error(`Run detail failed: ${detailResp.status}`);
        const detail: RunDetail = await detailResp.json();
        
        if (stepsResp.ok) {
          const steps = await stepsResp.json();
          setRunDetail({ ...detail, steps });
        } else {
          setRunDetail(detail);
        }
        setError(null);
      } catch (err) {
        console.warn(`Falling back to mock run ${selectedId}`, err);
        setRunDetail(fallbackDetails[selectedId] || null);
        setError('Using fallback data');
      } finally {
        setDetailLoading(false);
      }
    };

    loadDetail();
  }, [selectedId]);

  if (loading && runs.length === 0) {
    return <LoadingSpinner message="Loading runs..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
          Run Inspector
        </h1>
        <p className="text-gray-600" style={{ margin: 0 }}>
          Detailed inspection and analysis of individual scraper runs
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

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem' }}>
        <div>
          <RunListTable runs={runs} onSelect={handleSelect} />
        </div>
        <div>
          {detailLoading ? (
            <div className="card">
              <LoadingSpinner message="Loading run details..." />
            </div>
          ) : selectedId && runDetail ? (
            <RunDetailPanel run={runDetail} />
          ) : (
            <div className="card">
              <div className="empty-state">
                <div className="empty-state-icon">🔍</div>
                <p className="text-gray-500">Select a run to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RunInspector;
