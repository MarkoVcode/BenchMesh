/**
 * LogsPanel - API request history display
 *
 * Shows chronological history of all API requests made to instruments
 * with full details including timestamp, method, URL, status, and duration.
 */

import React, { useState } from 'react';
import { VscTrash, VscFilter, VscCheck, VscError, VscWarning } from 'react-icons/vsc';
import { useRequestLog } from '../../RequestLogContext';

export const LogsPanel: React.FC = () => {
  const { logs, clearLogs } = useRequestLog();
  const [filterMethod, setFilterMethod] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');

  // Filter logs based on selected filters
  const filteredLogs = logs.filter((log) => {
    if (filterMethod !== 'ALL' && log.method !== filterMethod) return false;

    if (filterStatus === 'SUCCESS' && (!log.status || log.status >= 400)) return false;
    if (filterStatus === 'ERROR' && (log.status === undefined || log.status < 400) && !log.error) return false;

    return true;
  });

  const formatTimestamp = (date: Date) => {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}.${date.getMilliseconds().toString().padStart(3, '0')}`;
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getStatusIcon = (log: typeof logs[0]) => {
    if (log.error) {
      return <VscError className="log-entry__status-icon log-entry__status-icon--error" />;
    }
    if (log.status && log.status >= 400) {
      return <VscWarning className="log-entry__status-icon log-entry__status-icon--warning" />;
    }
    return <VscCheck className="log-entry__status-icon log-entry__status-icon--success" />;
  };

  const getStatusClass = (log: typeof logs[0]) => {
    if (log.error) return 'log-entry--error';
    if (log.status && log.status >= 400) return 'log-entry--warning';
    return 'log-entry--success';
  };

  const extractEndpoint = (url: string) => {
    try {
      const urlObj = new URL(url);
      return urlObj.pathname;
    } catch {
      return url;
    }
  };

  return (
    <div className="logs-panel">
      <div className="logs-panel__toolbar">
        <div className="logs-panel__filters">
          <div className="logs-panel__filter-group">
            <VscFilter size={14} />
            <span>Method:</span>
            <select
              value={filterMethod}
              onChange={(e) => setFilterMethod(e.target.value)}
              className="logs-panel__select"
            >
              <option value="ALL">All</option>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          <div className="logs-panel__filter-group">
            <span>Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="logs-panel__select"
            >
              <option value="ALL">All</option>
              <option value="SUCCESS">Success</option>
              <option value="ERROR">Error</option>
            </select>
          </div>
        </div>

        <div className="logs-panel__stats">
          <span className="logs-panel__count">
            {filteredLogs.length} {filteredLogs.length === 1 ? 'entry' : 'entries'}
          </span>
          <button
            className="logs-panel__clear"
            onClick={clearLogs}
            title="Clear all logs"
            disabled={logs.length === 0}
          >
            <VscTrash size={14} />
            <span>Clear</span>
          </button>
        </div>
      </div>

      <div className="logs-panel__content">
        {filteredLogs.length === 0 ? (
          <div className="logs-panel__empty">
            <p>No API requests logged yet</p>
            <span className="logs-panel__hint">
              Requests will appear here as instruments are controlled
            </span>
          </div>
        ) : (
          <div className="logs-panel__list">
            {filteredLogs.map((log) => (
              <div key={log.id} className={`log-entry ${getStatusClass(log)}`}>
                <div className="log-entry__header">
                  <div className="log-entry__timestamp">
                    <span className="log-entry__date">{formatDate(log.timestamp)}</span>
                    <span className="log-entry__time">{formatTimestamp(log.timestamp)}</span>
                  </div>

                  <div className="log-entry__method">
                    <span className={`log-entry__method-badge log-entry__method-badge--${log.method.toLowerCase()}`}>
                      {log.method}
                    </span>
                  </div>

                  <div className="log-entry__endpoint">{extractEndpoint(log.url)}</div>

                  <div className="log-entry__status">
                    {getStatusIcon(log)}
                    {log.status && (
                      <span className="log-entry__status-code">{log.status}</span>
                    )}
                    {log.error && (
                      <span className="log-entry__error-text">Error</span>
                    )}
                  </div>

                  {log.duration !== undefined && (
                    <div className="log-entry__duration">{log.duration}ms</div>
                  )}
                </div>

                {(log.instrument || log.action || log.parameters || log.error) && (
                  <div className="log-entry__details">
                    {log.instrument && (
                      <span className="log-entry__detail">
                        <strong>Instrument:</strong> {log.instrument}
                        {log.channel && ` / Ch${log.channel}`}
                      </span>
                    )}
                    {log.action && (
                      <span className="log-entry__detail">
                        <strong>Action:</strong> {log.action}
                      </span>
                    )}
                    {log.parameters && (
                      <span className="log-entry__detail">
                        <strong>Parameters:</strong> {JSON.stringify(log.parameters)}
                      </span>
                    )}
                    {log.error && (
                      <span className="log-entry__detail log-entry__detail--error">
                        <strong>Error:</strong> {log.error}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
