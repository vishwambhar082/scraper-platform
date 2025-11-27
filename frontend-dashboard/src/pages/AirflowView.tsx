import React, { useState, useEffect } from 'react';
import AirflowIframe from '../components/AirflowIframe';
import LoadingSpinner from '../components/LoadingSpinner';

const AirflowView: React.FC = () => {
  const [airflowUrl, setAirflowUrl] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAirflowInfo = async () => {
      try {
        const resp = await fetch('/api/airflow/runs');
        if (!resp.ok) throw new Error(`Failed to load Airflow info: ${resp.status}`);
        const data = await resp.json();
        
        // Try to construct Airflow URL from environment or use default
        const url = import.meta.env.VITE_AIRFLOW_URL || 'http://localhost:8080';
        setAirflowUrl(url);
        setError(null);
      } catch (err) {
        console.warn('Failed to load Airflow info', err);
        setError('Unable to connect to Airflow. Using default URL.');
        setAirflowUrl('http://localhost:8080');
      } finally {
        setLoading(false);
      }
    };

    loadAirflowInfo();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Loading Airflow view..." />;
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '2rem', fontWeight: 700 }}>
          Airflow View
        </h1>
        <p className="text-gray-600" style={{ margin: 0 }}>
          Embedded Airflow webserver for DAG monitoring and management
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

      <div className="card" style={{ padding: 0, height: 'calc(100vh - 200px)', minHeight: '600px' }}>
        <div
          style={{
            padding: '1rem',
            borderBottom: '1px solid var(--color-gray-200)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Airflow UI</h3>
            <p className="text-xs text-gray-500" style={{ margin: '0.25rem 0 0 0' }}>
              {airflowUrl}
            </p>
          </div>
          <a
            href={airflowUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary btn-sm"
          >
            Open in New Tab →
          </a>
        </div>
        <div style={{ height: 'calc(100% - 80px)', position: 'relative' }}>
          <AirflowIframe url={airflowUrl} />
        </div>
      </div>
    </div>
  );
};

export default AirflowView;
