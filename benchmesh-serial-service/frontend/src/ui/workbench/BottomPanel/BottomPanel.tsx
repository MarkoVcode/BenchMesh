/**
 * BottomPanel - Tabbed panel for graphs, recordings, history, etc.
 *
 * Tabs:
 * - Graphs: Live measurement charts
 * - Records: Measurement table
 * - History: Request history
 * - NodeRED: Embedded Node-RED editor
 */

import React, { useState } from 'react';
import { VscClose, VscGraph, VscTable, VscHistory, VscExtensions, VscLinkExternal } from 'react-icons/vsc';
import { LogsPanel } from './LogsPanel';
import { NodeRedPanel } from './NodeRedPanel';
import './bottom-panel.css';

type TabType = 'graphs' | 'records' | 'history' | 'nodered';

interface BottomPanelProps {
  instruments?: any[];
  registry?: any;
  onClose: () => void;
}

export const BottomPanel: React.FC<BottomPanelProps> = ({
  instruments = [],
  registry = {},
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('graphs');

  const tabs = [
    { id: 'graphs', label: 'Graphs', icon: VscGraph },
    { id: 'records', label: 'Records', icon: VscTable },
    { id: 'history', label: 'History', icon: VscHistory },
    { id: 'nodered', label: 'Automation', icon: VscExtensions },
  ] as const;

  return (
    <div className="bottom-panel" data-testid="bottom-panel">
      <div className="bottom-panel__tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`bottom-panel__tab ${activeTab === tab.id ? 'bottom-panel__tab--active' : ''}`}
              onClick={() => setActiveTab(tab.id as TabType)}
              data-testid={`bottom-panel-tab-${tab.id}`}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
        <div className="bottom-panel__spacer" />
        <button
          className="bottom-panel__close"
          onClick={onClose}
          title="Close panel"
          aria-label="Close panel"
        >
          <VscClose size={16} />
        </button>
      </div>

      <div className="bottom-panel__content">
        {activeTab === 'graphs' && (
          <div className="bottom-panel__placeholder">
            <p>Graphs Panel - GraphPanel migration pending</p>
          </div>
        )}
        {activeTab === 'records' && (
          <div className="bottom-panel__placeholder">
            <p>Records Panel - RecordPanel migration pending</p>
          </div>
        )}
        {activeTab === 'history' && <LogsPanel />}
        {activeTab === 'nodered' && <NodeRedPanel />}
      </div>
    </div>
  );
};
