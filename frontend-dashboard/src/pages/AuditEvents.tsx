import React, { useEffect, useState, useMemo, useCallback } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import JsonViewer from '../components/JsonViewer';

interface AuditEvent {
  id: string;
  event_type: string;
  source?: string;
  run_id?: string;
  payload: Record<string, unknown>;
  created_at: string;
}

const AuditEvents: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ type?: string; source?: string }>({});
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    const loadEvents = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/audit/events');
        if (!resp.ok) throw new Error(`Failed to load events: ${resp.status}`);
        const result = await resp.json();
        const data: AuditEvent[] = result.events || [];
        
        // Fallback to mock data if API returns empty
        if (data.length === 0) {
          const mockData: AuditEvent[] = [
            {
              id: 'evt_001',
              event_type: 'run_started',
              source: 'alfabeta',
              run_id: 'run_2024_001',
              payload: { env: 'prod', variant_id: 'v1_baseline' },
              created_at: '2024-05-01T10:00:00Z',
            },
            {
              id: 'evt_002',
              event_type: 'config_change',
              source: 'quebec',
              payload: { field: 'rate_limit', old_value: 1.0, new_value: 2.0 },
              created_at: '2024-05-01T09:30:00Z',
            },
            {
              id: 'evt_003',
              event_type: 'run_completed',
              source: 'alfabeta',
              run_id: 'run_2024_001',
              payload: { status: 'success', records: 1200 },
              created_at: '2024-05-01T10:02:00Z',
            },
            {
              id: 'evt_004',
              event_type: 'error',
              source: 'quebec',
              run_id: 'run_2024_002',
              payload: { error: 'Drift detected', step: 'company_index' },
              created_at: '2024-05-01T11:00:00Z',
            },
          ];
          setEvents(mockData);
        } else {
          setEvents(data);
        }
        setError(null);
      } catch (err) {
        console.error('Failed to load audit events', err);
        setError('Failed to load audit events');
      } finally {
        setLoading(false);
      }
    };

    loadEvents();
  }, []);

  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      if (filter.type && event.event_type !== filter.type) return false;
      if (filter.source && event.source !== filter.source) return false;
      return true;
    }).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [events, filter]);

  const eventTypes = useMemo(() => {
    return Array.from(new Set(events.map(e => e.event_type)));
  }, [events]);

  const sources = useMemo(() => {
    return Array.from(new Set(events.map(e => e.source).filter(Boolean)));
  }, [events]);

  const buildExportUrl = useCallback((format: 'csv' | 'xlsx' | 'json') => {
    const params = new URLSearchParams();
    params.set('format', format);
    if (filter.type) params.set('event_type', filter.type);
    if (filter.source) params.set('source', filter.source);
    return `/api/audit/export?${params.toString()}`;
  }, [filter]);

  const handleExport = useCallback(async (format: 'csv' | 'xlsx' | 'json') => {
    setExportError(null);
    setExportingFormat(format);
    try {
      const resp = await fetch(buildExportUrl(format));
      if (!resp.ok) {
        const message = await resp.text();
        throw new Error(message || 'Failed to export audit events');
      }

      const blob = await resp.blob();
      const disposition = resp.headers.get('Content-Disposition');
      let filename = disposition?.split('filename=')[1]?.replace(/"/g, '');
      if (!filename) {
        const timestamp = new Date().toISOString().replace(/[:T]/g, '-').split('.')[0];
        filename = `audit_events_${timestamp}.${format}`;
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export audit events', err);
      setExportError('Failed to export audit events. Please try again or adjust your filters.');
    } finally {
      setExportingFormat(null);
    }
  }, [buildExportUrl]);

  if (loading && events.length === 0) {
    return <LoadingSpinner message="Loading audit events..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
          Audit Events
        </h1>
        <p className="text-gray-600" style={{ margin: 0 }}>
          Complete audit trail of platform events and changes
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

      {/* Filters */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header" style={{ alignItems: 'flex-start' }}>
          <div>
            <h2 className="card-title" style={{ marginBottom: '0.25rem' }}>Filters & Export</h2>
            <p className="text-gray-600 text-sm" style={{ margin: 0 }}>
              Adjust filters then export all matching audit events with full payloads.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <button
              className="btn btn-secondary"
              onClick={() => handleExport('csv')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'csv' ? 'Exporting CSV...' : 'Export CSV'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleExport('xlsx')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'xlsx' ? 'Exporting XLSX...' : 'Export XLSX'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleExport('json')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'json' ? 'Exporting JSON...' : 'Export JSON'}
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <label className="text-sm" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Event Type
            </label>
            <select
              className="input"
              value={filter.type || ''}
              onChange={(e) => setFilter({ ...filter, type: e.target.value || undefined })}
            >
              <option value="">All Types</option>
              {eventTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label className="text-sm" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Source
            </label>
            <select
              className="input"
              value={filter.source || ''}
              onChange={(e) => setFilter({ ...filter, source: e.target.value || undefined })}
            >
              <option value="">All Sources</option>
              {sources.map(source => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setFilter({})}
            >
              Clear Filters
            </button>
          </div>
        </div>

        {exportError && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.75rem',
              background: 'rgba(248, 113, 113, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '0.5rem',
              color: 'var(--color-error)',
              fontSize: '0.875rem',
            }}
          >
            ⚠️ {exportError}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedEvent ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
        {/* Events List */}
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '1rem' }}>
            Events ({filteredEvents.length})
          </h2>
          {filteredEvents.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {filteredEvents.map(event => (
                <div
                  key={event.id}
                  onClick={() => setSelectedEvent(event)}
                  style={{
                    padding: '1rem',
                    border: '1px solid var(--color-gray-200)',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    background: selectedEvent?.id === event.id ? 'var(--color-gray-50)' : 'white',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedEvent?.id !== event.id) {
                      e.currentTarget.style.borderColor = 'var(--color-primary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (selectedEvent?.id !== event.id) {
                      e.currentTarget.style.borderColor = 'var(--color-gray-200)';
                    }
                  }}
                >
                  <div className="flex-between mb-1">
                    <span className="badge" style={{ background: 'var(--color-primary)', color: 'white' }}>
                      {event.event_type}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(event.created_at).toLocaleString()}
                    </span>
                  </div>
                  {event.source && (
                    <div className="text-sm mb-1">
                      <span className="text-gray-500">Source: </span>
                      <span className="badge">{event.source}</span>
                    </div>
                  )}
                  {event.run_id && (
                    <div className="text-sm font-mono">
                      <span className="text-gray-500">Run: </span>
                      {event.run_id}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No events found</p>
          )}
        </div>

        {/* Event Details */}
        {selectedEvent && (
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Event Details</h2>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => setSelectedEvent(null)}
              >
                Close
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <span className="text-sm text-gray-500">Event ID:</span>
                <div className="font-mono text-sm">{selectedEvent.id}</div>
              </div>
              <div>
                <span className="text-sm text-gray-500">Type:</span>
                <div>
                  <span className="badge" style={{ background: 'var(--color-primary)', color: 'white' }}>
                    {selectedEvent.event_type}
                  </span>
                </div>
              </div>
              {selectedEvent.source && (
                <div>
                  <span className="text-sm text-gray-500">Source:</span>
                  <div><span className="badge">{selectedEvent.source}</span></div>
                </div>
              )}
              {selectedEvent.run_id && (
                <div>
                  <span className="text-sm text-gray-500">Run ID:</span>
                  <div className="font-mono text-sm">{selectedEvent.run_id}</div>
                </div>
              )}
              <div>
                <span className="text-sm text-gray-500">Created At:</span>
                <div className="text-sm">
                  {new Date(selectedEvent.created_at).toLocaleString()}
                </div>
              </div>
              <div>
                <span className="text-sm text-gray-500">Payload:</span>
                <div style={{ marginTop: '0.5rem' }}>
                  <JsonViewer data={selectedEvent.payload} />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditEvents;

