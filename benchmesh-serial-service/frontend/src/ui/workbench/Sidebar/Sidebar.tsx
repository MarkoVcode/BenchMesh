/**
 * Sidebar - Collapsible sidebar with view routing
 *
 * Displays different views based on activeView:
 * - instruments: List of all configured instruments
 * - settings: Device configuration
 * - recording: Recording management
 * - metrics: Performance metrics
 */

import React from 'react';
import { VscClose } from 'react-icons/vsc';
import { ViewType } from '../WorkbenchLayout';
import { InstrumentListView } from './InstrumentListView';
import { RecordingView } from './RecordingView';
import './sidebar.css';

interface SidebarProps {
  activeView: ViewType;
  instruments?: any[];
  registry?: any;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  instruments = [],
  registry = {},
  onClose,
}) => {
  const viewTitles: Record<ViewType, string> = {
    instruments: 'Instruments',
    settings: 'Settings',
    recording: 'Recording',
    metrics: 'Metrics',
  };

  return (
    <div className="sidebar" data-testid="sidebar">
      <div className="sidebar__header">
        <h2 className="sidebar__title">{viewTitles[activeView]}</h2>
        <button
          className="sidebar__close"
          onClick={onClose}
          title="Close sidebar"
          aria-label="Close sidebar"
        >
          <VscClose size={16} />
        </button>
      </div>

      <div className="sidebar__content">
        {activeView === 'instruments' && (
          <InstrumentListView
            instruments={instruments}
            registry={registry}
          />
        )}
        {activeView === 'settings' && (
          <div className="sidebar__placeholder">
            <p>Settings view - Config migration pending</p>
          </div>
        )}
        {activeView === 'recording' && <RecordingView />}
        {activeView === 'metrics' && (
          <div className="sidebar__placeholder">
            <p>Metrics view - Migration pending</p>
          </div>
        )}
      </div>
    </div>
  );
};
