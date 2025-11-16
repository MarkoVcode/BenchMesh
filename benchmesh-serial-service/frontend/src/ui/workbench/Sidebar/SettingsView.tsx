/**
 * SettingsView - Application settings sidebar
 *
 * Tabs:
 * - Instruments: Instrument configuration
 * - Miscellaneous: App settings (history retention, etc.)
 */

import React, { useState, useEffect } from 'react';
import { VscTools, VscGear } from 'react-icons/vsc';
import { InstrumentConfigView } from './InstrumentConfigView';
import './sidebar.css';

type SettingsTab = 'instruments' | 'miscellaneous';

interface SettingsViewProps {
  apiBase: string;
  onConfigUpdated: () => void;
  autoAddInstrument?: boolean;
  onAutoAddComplete?: () => void;
}

// History retention options in days
const RETENTION_OPTIONS = [
  { value: 1, label: '1 day' },
  { value: 3, label: '3 days' },
  { value: 5, label: '5 days' },
  { value: 7, label: '7 days' },
] as const;

const DEFAULT_RETENTION_DAYS = 3;
const STORAGE_KEY_RETENTION = 'benchmesh:historyRetentionDays';

export const SettingsView: React.FC<SettingsViewProps> = ({ apiBase, onConfigUpdated, autoAddInstrument, onAutoAddComplete }) => {
  const [activeTab, setActiveTab] = useState<SettingsTab>('instruments');
  const [historyRetention, setHistoryRetention] = useState<number>(() => {
    // Load from localStorage on mount
    try {
      const saved = localStorage.getItem(STORAGE_KEY_RETENTION);
      if (saved) {
        const parsed = parseInt(saved, 10);
        // Validate it's one of our allowed values
        if (RETENTION_OPTIONS.some(opt => opt.value === parsed)) {
          return parsed;
        }
      }
    } catch (e) {
      console.error('Failed to load history retention setting:', e);
    }
    return DEFAULT_RETENTION_DAYS;
  });

  // Save retention setting to localStorage when it changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_RETENTION, historyRetention.toString());

      // Dispatch custom event to notify RequestLogContext to cleanup
      window.dispatchEvent(new CustomEvent('benchmesh:historyRetentionChanged', {
        detail: { retentionDays: historyRetention }
      }));
    } catch (e) {
      console.error('Failed to save history retention setting:', e);
    }
  }, [historyRetention]);

  const handleRetentionChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = parseInt(event.target.value, 10);
    setHistoryRetention(value);
  };

  const tabs = [
    { id: 'instruments', label: 'Instruments', icon: VscTools },
    { id: 'miscellaneous', label: 'Miscellaneous', icon: VscGear },
  ] as const;

  return (
    <div className="settings-view" data-testid="settings-view">
      {/* Tab Bar */}
      <div className="settings-view__tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`settings-view__tab ${activeTab === tab.id ? 'settings-view__tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id as SettingsTab)}
              data-testid={`settings-tab-${tab.id}`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="settings-view__content">
        {activeTab === 'instruments' && (
          <InstrumentConfigView
            apiBase={apiBase}
            onConfigUpdated={onConfigUpdated}
            autoAddNew={autoAddInstrument}
            onAutoAddComplete={onAutoAddComplete}
          />
        )}

        {activeTab === 'miscellaneous' && (
          <div className="settings-view__sections">
            {/* History & Logs Section */}
            <div className="settings-view__section">
              <h3 className="settings-view__section-title">History & Logs</h3>

              <div className="settings-view__setting">
                <label htmlFor="history-retention" className="settings-view__label">
                  History Retention
                  <span className="settings-view__label-hint">
                    How long to keep request history
                  </span>
                </label>
                <select
                  id="history-retention"
                  className="settings-view__dropdown"
                  value={historyRetention}
                  onChange={handleRetentionChange}
                  data-testid="history-retention-dropdown"
                >
                  {RETENTION_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <p className="settings-view__section-description">
                Request history older than {historyRetention} {historyRetention === 1 ? 'day' : 'days'} will be automatically removed.
                History is stored locally in your browser.
              </p>
            </div>

            {/* Future sections can be added here */}
          </div>
        )}
      </div>
    </div>
  );
};
