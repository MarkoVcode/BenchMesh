/**
 * RequestLogContext - Global request history tracking with persistence
 *
 * Provides a context for logging API requests made to instruments.
 * Each log entry includes timestamp, method, URL, parameters, and response status.
 *
 * Features:
 * - localStorage persistence (survives page refresh)
 * - Configurable retention period (cleanup old logs)
 * - Automatic periodic cleanup
 */

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';

export interface RequestLogEntry {
  id: string;
  timestamp: Date;
  method: string;
  url: string;
  status?: number;
  statusText?: string;
  duration?: number;
  error?: string;
  // Additional context
  instrument?: string;
  channel?: string;
  action?: string;
  parameters?: any;
}

interface RequestLogContextValue {
  logs: RequestLogEntry[];
  addLog: (entry: Omit<RequestLogEntry, 'id' | 'timestamp'>) => void;
  clearLogs: () => void;
}

// Storage keys
const STORAGE_KEY_LOGS = 'benchmesh:requestLogs';
const STORAGE_KEY_RETENTION = 'benchmesh:historyRetentionDays';
const DEFAULT_RETENTION_DAYS = 3;
const MAX_LOGS = 1000;
const CLEANUP_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

// Retention periods in milliseconds
const RETENTION_MS = {
  1: 1 * 24 * 60 * 60 * 1000,
  3: 3 * 24 * 60 * 60 * 1000,
  5: 5 * 24 * 60 * 60 * 1000,
  7: 7 * 24 * 60 * 60 * 1000,
} as const;

/**
 * Get retention period in milliseconds from localStorage
 */
function getRetentionMs(): number {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_RETENTION);
    if (saved) {
      const days = parseInt(saved, 10) as keyof typeof RETENTION_MS;
      if (RETENTION_MS[days]) {
        return RETENTION_MS[days];
      }
    }
  } catch (e) {
    console.error('Failed to load retention setting:', e);
  }
  return RETENTION_MS[DEFAULT_RETENTION_DAYS];
}

/**
 * Clean up logs older than retention period
 */
function cleanupOldLogs(logs: RequestLogEntry[], retentionMs: number): RequestLogEntry[] {
  const cutoffTime = Date.now() - retentionMs;
  return logs.filter(log => log.timestamp.getTime() > cutoffTime);
}

/**
 * Load logs from localStorage with cleanup
 */
function loadLogsFromStorage(): RequestLogEntry[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_LOGS);
    if (saved) {
      const parsed = JSON.parse(saved);
      // Convert ISO strings back to Date objects
      const logsWithDates = parsed.map((log: any) => ({
        ...log,
        timestamp: new Date(log.timestamp),
      }));
      // Clean up old logs on load
      const retentionMs = getRetentionMs();
      return cleanupOldLogs(logsWithDates, retentionMs);
    }
  } catch (e) {
    console.error('Failed to load logs from localStorage:', e);
  }
  return [];
}

/**
 * Save logs to localStorage
 */
function saveLogsToStorage(logs: RequestLogEntry[]) {
  try {
    // Convert Dates to ISO strings for JSON serialization
    const logsWithISODates = logs.map(log => ({
      ...log,
      timestamp: log.timestamp.toISOString(),
    }));
    localStorage.setItem(STORAGE_KEY_LOGS, JSON.stringify(logsWithISODates));
  } catch (e) {
    console.error('Failed to save logs to localStorage:', e);
  }
}

const RequestLogContext = createContext<RequestLogContextValue | undefined>(undefined);

export function RequestLogProvider({ children }: { children: ReactNode }) {
  // Initialize logs from localStorage
  const [logs, setLogs] = useState<RequestLogEntry[]>(() => loadLogsFromStorage());

  // Save logs to localStorage whenever they change (debounced via React's batching)
  useEffect(() => {
    saveLogsToStorage(logs);
  }, [logs]);

  // Periodic cleanup (every 5 minutes)
  useEffect(() => {
    const cleanupInterval = setInterval(() => {
      setLogs((prevLogs) => {
        const retentionMs = getRetentionMs();
        const cleaned = cleanupOldLogs(prevLogs, retentionMs);
        // Only update if cleanup actually removed logs
        return cleaned.length < prevLogs.length ? cleaned : prevLogs;
      });
    }, CLEANUP_INTERVAL_MS);

    return () => clearInterval(cleanupInterval);
  }, []);

  // Listen for retention setting changes from SettingsView
  useEffect(() => {
    const handleRetentionChange = () => {
      setLogs((prevLogs) => {
        const retentionMs = getRetentionMs();
        return cleanupOldLogs(prevLogs, retentionMs);
      });
    };

    window.addEventListener('benchmesh:historyRetentionChanged', handleRetentionChange);
    return () => window.removeEventListener('benchmesh:historyRetentionChanged', handleRetentionChange);
  }, []);

  const addLog = useCallback((entry: Omit<RequestLogEntry, 'id' | 'timestamp'>) => {
    const newLog: RequestLogEntry = {
      ...entry,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
    };

    setLogs((prev) => {
      // Add new log and enforce max limit
      const updated = [newLog, ...prev];
      return updated.slice(0, MAX_LOGS);
    });
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return (
    <RequestLogContext.Provider value={{ logs, addLog, clearLogs }}>
      {children}
    </RequestLogContext.Provider>
  );
}

export function useRequestLog() {
  const context = useContext(RequestLogContext);
  if (!context) {
    throw new Error('useRequestLog must be used within a RequestLogProvider');
  }
  return context;
}

/**
 * Logging fetch wrapper - automatically logs requests
 */
export async function loggedFetch(
  url: string,
  options: RequestInit & {
    instrument?: string;
    channel?: string;
    action?: string;
    parameters?: any;
    addLog: (entry: Omit<RequestLogEntry, 'id' | 'timestamp'>) => void;
  }
): Promise<Response> {
  const { instrument, channel, action, parameters, addLog, ...fetchOptions } = options;
  const method = fetchOptions.method || 'GET';
  const startTime = Date.now();

  try {
    const response = await fetch(url, fetchOptions);
    const duration = Date.now() - startTime;

    addLog({
      method,
      url,
      status: response.status,
      statusText: response.statusText,
      duration,
      instrument,
      channel,
      action,
      parameters,
    });

    return response;
  } catch (error: any) {
    const duration = Date.now() - startTime;

    addLog({
      method,
      url,
      duration,
      error: error.message || 'Network error',
      instrument,
      channel,
      action,
      parameters,
    });

    throw error;
  }
}
