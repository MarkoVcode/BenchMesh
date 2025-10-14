import React, { useEffect, useState } from 'react';
import { RecordingApi, RecordingSeries } from '../../api/recordingApi';

interface RecordingListProps {
  apiBase: string;
  onViewDetails: (seriesId: number) => void;
  refreshTrigger: number;
}

export const RecordingList: React.FC<RecordingListProps> = ({ apiBase, onViewDetails, refreshTrigger }) => {
  const [recordings, setRecordings] = useState<RecordingSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<{ [key: number]: string }>({});

  const api = new RecordingApi(apiBase);

  const loadRecordings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listRecordings();
      setRecordings(response.recordings);
    } catch (err: any) {
      console.error('[RecordingList] Failed to load recordings:', err);
      setError(err.message || 'Failed to load recordings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecordings();
    // Refresh every 5 seconds to show live updates
    const interval = setInterval(loadRecordings, 5000);
    return () => clearInterval(interval);
  }, [apiBase, refreshTrigger]);

  const handlePause = async (seriesId: number) => {
    setActionLoading({ ...actionLoading, [seriesId]: 'pausing' });
    try {
      await api.pauseRecording(seriesId);
      await loadRecordings();
    } catch (err: any) {
      console.error('[RecordingList] Failed to pause recording:', err);
      alert(`Failed to pause: ${err.response?.data?.detail || err.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [seriesId]: '' });
    }
  };

  const handleResume = async (seriesId: number) => {
    setActionLoading({ ...actionLoading, [seriesId]: 'resuming' });
    try {
      await api.resumeRecording(seriesId);
      await loadRecordings();
    } catch (err: any) {
      console.error('[RecordingList] Failed to resume recording:', err);
      alert(`Failed to resume: ${err.response?.data?.detail || err.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [seriesId]: '' });
    }
  };

  const handleStop = async (seriesId: number) => {
    if (!confirm('Are you sure you want to stop this recording? This cannot be undone.')) {
      return;
    }
    setActionLoading({ ...actionLoading, [seriesId]: 'stopping' });
    try {
      await api.stopRecording(seriesId);
      await loadRecordings();
    } catch (err: any) {
      console.error('[RecordingList] Failed to stop recording:', err);
      alert(`Failed to stop: ${err.response?.data?.detail || err.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [seriesId]: '' });
    }
  };

  const handleDelete = async (seriesId: number) => {
    if (!confirm('Are you sure you want to delete this recording? All data will be lost.')) {
      return;
    }
    setActionLoading({ ...actionLoading, [seriesId]: 'deleting' });
    try {
      await api.deleteRecording(seriesId);
      await loadRecordings();
    } catch (err: any) {
      console.error('[RecordingList] Failed to delete recording:', err);
      alert(`Failed to delete: ${err.response?.data?.detail || err.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [seriesId]: '' });
    }
  };

  const handleExport = async (seriesId: number, name: string) => {
    setActionLoading({ ...actionLoading, [seriesId]: 'exporting' });
    try {
      const blob = await api.exportToCsv(seriesId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name.replace(/\s+/g, '_')}_${seriesId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('[RecordingList] Failed to export recording:', err);
      alert(`Failed to export: ${err.response?.data?.detail || err.message}`);
    } finally {
      setActionLoading({ ...actionLoading, [seriesId]: '' });
    }
  };

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      recording: '#52c41a',
      paused: '#faad14',
      stopped: '#d9d9d9'
    };
    return (
      <span style={{
        padding: '3px 10px',
        borderRadius: '12px',
        background: colors[status] || '#d9d9d9',
        color: 'white',
        fontSize: '12px',
        fontWeight: 'bold',
        textTransform: 'uppercase'
      }}>
        {status}
      </span>
    );
  };

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading recordings...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#ff4d4f' }}>
        Error: {error}
      </div>
    );
  }

  if (recordings.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-2)' }}>
        No recordings yet. Start a new recording above.
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <h3 style={{ marginTop: 0 }}>All Recordings</h3>
      {recordings.map((recording) => (
        <div
          key={recording.id}
          style={{
            padding: '15px',
            background: 'var(--bg-1)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            marginBottom: '15px'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '10px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '5px' }}>
                <h4 style={{ margin: 0 }}>{recording.name}</h4>
                {getStatusBadge(recording.status)}
              </div>
              {recording.description && (
                <p style={{ margin: '5px 0', color: 'var(--text-1)', fontSize: '14px' }}>{recording.description}</p>
              )}
              <div style={{ fontSize: '12px', color: 'var(--text-2)' }}>
                <div>ID: {recording.id}</div>
                <div>Started: {new Date(recording.start_time).toLocaleString()}</div>
                {recording.end_time && <div>Ended: {new Date(recording.end_time).toLocaleString()}</div>}
                <div>Duration: {formatDuration(recording.total_duration_seconds)}</div>
                <div>Interval: {recording.interval_seconds}s</div>
                <div>Channels: {recording.channels.length}</div>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {recording.status === 'recording' && (
              <>
                <button
                  onClick={() => handlePause(recording.id)}
                  disabled={!!actionLoading[recording.id]}
                  style={{
                    padding: '8px 12px',
                    background: '#faad14',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {actionLoading[recording.id] === 'pausing' ? 'Pausing...' : '⏸ Pause'}
                </button>
                <button
                  onClick={() => handleStop(recording.id)}
                  disabled={!!actionLoading[recording.id]}
                  style={{
                    padding: '8px 12px',
                    background: '#ff4d4f',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {actionLoading[recording.id] === 'stopping' ? 'Stopping...' : '⏹ Stop'}
                </button>
              </>
            )}

            {recording.status === 'paused' && (
              <>
                <button
                  onClick={() => handleResume(recording.id)}
                  disabled={!!actionLoading[recording.id]}
                  style={{
                    padding: '8px 12px',
                    background: '#52c41a',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {actionLoading[recording.id] === 'resuming' ? 'Resuming...' : '▶ Resume'}
                </button>
                <button
                  onClick={() => handleStop(recording.id)}
                  disabled={!!actionLoading[recording.id]}
                  style={{
                    padding: '8px 12px',
                    background: '#ff4d4f',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                    fontSize: '14px'
                  }}
                >
                  {actionLoading[recording.id] === 'stopping' ? 'Stopping...' : '⏹ Stop'}
                </button>
              </>
            )}

            <button
              onClick={() => onViewDetails(recording.id)}
              disabled={!!actionLoading[recording.id]}
              style={{
                padding: '8px 12px',
                background: '#1890ff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                fontSize: '14px'
              }}
            >
              📊 View Details
            </button>

            <button
              onClick={() => handleExport(recording.id, recording.name)}
              disabled={!!actionLoading[recording.id]}
              style={{
                padding: '8px 12px',
                background: '#722ed1',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                fontSize: '14px'
              }}
            >
              {actionLoading[recording.id] === 'exporting' ? 'Exporting...' : '💾 Export CSV'}
            </button>

            {recording.status === 'stopped' && (
              <button
                onClick={() => handleDelete(recording.id)}
                disabled={!!actionLoading[recording.id]}
                style={{
                  padding: '8px 12px',
                  background: '#ff4d4f',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: actionLoading[recording.id] ? 'not-allowed' : 'pointer',
                  fontSize: '14px'
                }}
              >
                {actionLoading[recording.id] === 'deleting' ? 'Deleting...' : '🗑 Delete'}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
