import React, { useState, useEffect } from 'react';
import { experimentsApi, Experiment, ExperimentRunResponse } from '../services/experimentsApi';

const ExperimentsPage: React.FC = () => {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<string>('');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<ExperimentRunResponse | null>(null);
  const [config, setConfig] = useState<any>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchExperiments();
  }, []);

  const fetchExperiments = async () => {
    try {
      const data = await experimentsApi.listExperiments();
      setExperiments(data.experiments || []);
    } catch (error) {
      console.error('Failed to fetch experiments:', error);
      setError('Failed to load experiments. Make sure the backend is running.');
    }
  };

  const runExperiment = async () => {
    if (!selectedExperiment) return;

    setRunning(true);
    setResults(null);
    setError(null);

    try {
      const data = await experimentsApi.runExperiment({
        experiment_type: selectedExperiment,
        config: config,
      });
      setResults(data);
      
      // If run_id is available, start polling for results
      if (data.run_id) {
        // Poll for results every 2 seconds until complete
        const pollInterval = setInterval(async () => {
          try {
            const detailedResults = await experimentsApi.getResults(data.run_id);
            const newStatus = detailedResults.status || 'running';
            setResults(prev => prev ? { 
              ...prev, 
              results: detailedResults, 
              status: newStatus
            } : null);
            
            // Stop polling if experiment is complete or failed
            if (newStatus === 'completed' || newStatus === 'failed') {
              clearInterval(pollInterval);
              setRunning(false);
            }
          } catch (err) {
            console.error('Failed to fetch detailed results:', err);
            // Don't clear interval on error, keep trying
          }
        }, 2000);
        
        // Store interval ID for cleanup
        (window as any).__experimentPollInterval = pollInterval;
      }
    } catch (error: any) {
      console.error('Failed to run experiment:', error);
      setError(error.message || 'Failed to run experiment');
      setResults({
        run_id: '',
        experiment_type: selectedExperiment,
        status: 'failed',
        results: { error: error.message || String(error) },
      });
      setRunning(false);
    }
  };

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if ((window as any).__experimentPollInterval) {
        clearInterval((window as any).__experimentPollInterval);
      }
    };
  }, []);

  const getExperimentConfig = (type: string) => {
    const configs: Record<string, any> = {
      e1: { num_tasks: 100, max_parallel: 10 },
      e2: { max_iterations: 5 },
      e3: { num_stacks: 10 },
      e4: { num_sessions: 100, canvas_sizes: [100, 500] },
    };
    return configs[type] || {};
  };

  const handleExperimentChange = (type: string) => {
    setSelectedExperiment(type);
    setConfig(getExperimentConfig(type));
  };

  return (
    <div style={{ 
      padding: '2rem', 
      maxWidth: '1200px', 
      margin: '0 auto', 
      color: '#e5e7eb',
      minHeight: '100vh'
    }}>
      <h1 style={{ color: '#f9fafb', marginBottom: '1.5rem' }}>Experiments Dashboard</h1>
      
      {error && (
        <div style={{ 
          background: '#7f1d1d', 
          color: '#fca5a5', 
          padding: '1rem', 
          borderRadius: '4px', 
          marginBottom: '1rem',
          border: '1px solid #ef4444'
        }}>
          <strong style={{ color: '#fee' }}>Error:</strong> {error}
        </div>
      )}

      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ color: '#f9fafb', marginBottom: '1rem' }}>Available Experiments</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
          <div
            onClick={() => handleExperimentChange('e1')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e1' ? '2px solid #4285f4' : '1px solid #4b5563',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedExperiment === 'e1' ? '#1f2937' : '#1f2937',
              color: '#e5e7eb',
              transition: 'all 0.2s'
            }}
          >
            <h3 style={{ color: '#f9fafb', margin: '0 0 0.5rem 0' }}>E1: Parallelism</h3>
            <p style={{ color: '#d1d5db', margin: 0 }}>Measure throughput and speedup</p>
          </div>
          <div
            onClick={() => handleExperimentChange('e2')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e2' ? '2px solid #4285f4' : '1px solid #4b5563',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedExperiment === 'e2' ? '#1f2937' : '#1f2937',
              color: '#e5e7eb',
              transition: 'all 0.2s'
            }}
          >
            <h3 style={{ color: '#f9fafb', margin: '0 0 0.5rem 0' }}>E2: Deployability</h3>
            <p style={{ color: '#d1d5db', margin: 0 }}>Measure passItr@n</p>
          </div>
          <div
            onClick={() => handleExperimentChange('e3')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e3' ? '2px solid #4285f4' : '1px solid #4b5563',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedExperiment === 'e3' ? '#1f2937' : '#1f2937',
              color: '#e5e7eb',
              transition: 'all 0.2s'
            }}
          >
            <h3 style={{ color: '#f9fafb', margin: '0 0 0.5rem 0' }}>E3: Concurrency</h3>
            <p style={{ color: '#d1d5db', margin: 0 }}>Measure convergence and rollback</p>
          </div>
          <div
            onClick={() => handleExperimentChange('e4')}
            style={{
              padding: '1rem',
              border: selectedExperiment === 'e4' ? '2px solid #4285f4' : '1px solid #4b5563',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedExperiment === 'e4' ? '#1f2937' : '#1f2937',
              color: '#e5e7eb',
              transition: 'all 0.2s'
            }}
          >
            <h3 style={{ color: '#f9fafb', margin: '0 0 0.5rem 0' }}>E4: Canvas Performance</h3>
            <p style={{ color: '#d1d5db', margin: 0 }}>Measure WebSocket latency and FPS</p>
          </div>
        </div>
      </div>

      {selectedExperiment && (
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ color: '#f9fafb', marginBottom: '1rem' }}>Configuration</h2>
          <div style={{ marginBottom: '1rem' }}>
            <pre style={{ 
              background: '#1f2937', 
              padding: '1rem', 
              borderRadius: '4px',
              color: '#e5e7eb',
              border: '1px solid #4b5563',
              overflow: 'auto'
            }}>
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
          <button
            onClick={runExperiment}
            disabled={running}
            style={{
              padding: '0.75rem 1.5rem',
              background: running ? '#ccc' : '#4285f4',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: running ? 'not-allowed' : 'pointer',
            }}
          >
            {running ? 'Running...' : 'Run Experiment'}
          </button>
        </div>
      )}

      {results && (
        <div>
          <h2 style={{ color: '#f9fafb', marginBottom: '1rem' }}>Results</h2>
          <div style={{ 
            background: results.status === 'completed' ? '#064e3b' : results.status === 'failed' ? '#7f1d1d' : '#78350f',
            padding: '1rem', 
            borderRadius: '4px',
            border: `2px solid ${results.status === 'completed' ? '#10b981' : results.status === 'failed' ? '#ef4444' : '#f59e0b'}`,
            color: '#e5e7eb'
          }}>
            <p style={{ color: '#e5e7eb' }}><strong style={{ color: '#f9fafb' }}>Status:</strong> <span style={{ 
              color: results.status === 'completed' ? '#10b981' : results.status === 'failed' ? '#ef4444' : '#f59e0b',
              fontWeight: 'bold'
            }}>{results.status.toUpperCase()}</span></p>
            <p style={{ color: '#e5e7eb' }}><strong style={{ color: '#f9fafb' }}>Run ID:</strong> <code style={{ 
              background: '#1f2937', 
              padding: '0.25rem 0.5rem', 
              borderRadius: '4px',
              color: '#60a5fa',
              fontSize: '0.9rem'
            }}>{results.run_id}</code></p>
            {results.status === 'running' && (
              <p style={{ color: '#fbbf24' }}>⏳ Experiment is running... Results will appear when complete.</p>
            )}
            {results.results && (
              <div style={{ marginTop: '1rem' }}>
                <h3 style={{ color: '#f9fafb', marginBottom: '0.5rem' }}>Results Data:</h3>
                <pre style={{ 
                  background: '#1f2937', 
                  padding: '1rem', 
                  borderRadius: '4px', 
                  overflow: 'auto',
                  maxHeight: '400px',
                  fontSize: '12px',
                  color: '#e5e7eb',
                  border: '1px solid #4b5563'
                }}>
                  {JSON.stringify(results.results, null, 2)}
                </pre>
              </div>
            )}
            {results.run_id && results.status === 'running' && (
              <button
                onClick={async () => {
                  try {
                    const detailedResults = await experimentsApi.getResults(results.run_id);
                    setResults(prev => prev ? { ...prev, results: detailedResults, status: detailedResults.status || prev.status } : null);
                  } catch (err) {
                    console.error('Failed to fetch results:', err);
                  }
                }}
                style={{
                  marginTop: '1rem',
                  padding: '0.5rem 1rem',
                  background: '#4285f4',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Refresh Results
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExperimentsPage;

