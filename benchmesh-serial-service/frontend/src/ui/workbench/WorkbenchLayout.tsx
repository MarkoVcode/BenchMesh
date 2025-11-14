/**
 * WorkbenchLayout - Main container for the VS Code-inspired UI
 *
 * Layout structure:
 * ┌─────────────────────────────────────┐
 * │        ActivityBar │ Sidebar │ Editor │
 * │                    │         │        │
 * │                    │         ├────────┤
 * │                    │         │ Panel  │
 * └─────────────────────────────────────┘
 * │          StatusBar                  │
 * └─────────────────────────────────────┘
 */

import React, { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import {
  VscLayoutSidebarLeft,
  VscLayoutSidebarLeftOff,
  VscLayoutPanel,
  VscLayoutPanelOff,
  VscLayoutSidebarRight,
  VscLayoutSidebarRightOff,
  VscChromeMinimize,
  VscChromeMaximize,
  VscChromeClose
} from 'react-icons/vsc';
import { ActivityBar } from './ActivityBar/ActivityBar';
import { Sidebar } from './Sidebar/Sidebar';
import { EditorArea } from './EditorArea/EditorArea';
import { BottomPanel } from './BottomPanel/BottomPanel';
import { StatusBar } from './StatusBar/StatusBar';
import './styles/workbench.css';

export type ViewType = 'instruments' | 'settings' | 'recording' | 'metrics';

interface WorkbenchLayoutProps {
  instruments: any[];
  registry: any;
  apiBase: string;
  loading: boolean;
  error: string | null;
  wsDiag: { ok: boolean; msg: string; last: number | null };
  onOpenConfig: () => void;
  onOpenRecording: () => void;
  onOpenDocs: () => void;
  onOpenMetrics: () => void;
  onSwitchToClassic?: () => void;
  isElectron: boolean;
}

export const WorkbenchLayout: React.FC<WorkbenchLayoutProps> = ({
  instruments,
  registry,
  apiBase,
  loading,
  error,
  wsDiag,
  onOpenConfig,
  onOpenRecording,
  onOpenDocs,
  onOpenMetrics,
  onSwitchToClassic,
  isElectron
}) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true);
  const [bottomPanelCollapsed, setBottomPanelCollapsed] = useState(true);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(true); // Right panel not yet implemented
  const [activeView, setActiveView] = useState<ViewType>('instruments');

  // Initialize activeInstruments from localStorage
  const [activeInstruments, setActiveInstruments] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('benchmesh:activeInstruments');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error('Failed to load active instruments from localStorage:', e);
      return [];
    }
  });

  // Persist activeInstruments to localStorage whenever it changes
  React.useEffect(() => {
    try {
      localStorage.setItem('benchmesh:activeInstruments', JSON.stringify(activeInstruments));
    } catch (e) {
      console.error('Failed to save active instruments to localStorage:', e);
    }
  }, [activeInstruments]);

  const handleInstrumentClick = (instrumentId: string) => {
    setActiveInstruments((prev) => {
      if (prev.includes(instrumentId)) {
        // Toggle off - remove from active list
        return prev.filter((id) => id !== instrumentId);
      } else {
        // Toggle on - add to active list
        return [...prev, instrumentId];
      }
    });
  };

  const handleViewChange = (view: ViewType) => {
    setActiveView(view);
    if (sidebarCollapsed) {
      setSidebarCollapsed(false);
    }
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const handleToggleBottomPanel = () => {
    setBottomPanelCollapsed(!bottomPanelCollapsed);
  };

  const handleToggleRightPanel = () => {
    setRightPanelCollapsed(!rightPanelCollapsed);
  };

  const handleMinimize = () => {
    if (window.electron?.minimize) {
      window.electron.minimize();
    }
  };

  const handleMaximize = () => {
    if (window.electron?.maximize) {
      window.electron.maximize();
    }
  };

  const handleClose = () => {
    if (window.electron?.close) {
      window.electron.close();
    }
  };

  const apiOk = !loading && !error;

  return (
    <div className="workbench">
      {/* Header Bar */}
      <div className="topbar">
        <div className="brand">BenchMesh</div>
        <div className="topbar-center">
          <button
            className="config-button"
            onClick={onOpenConfig}
            title="Configure Instruments"
          >
            ⚙️ Configuration
          </button>
          <button
            className="config-button"
            onClick={onOpenRecording}
            title="Data Recording"
          >
            📊 Recording
          </button>
          {!isElectron && (
            <button
              className="config-button"
              onClick={onOpenDocs}
              title="View Documentation"
            >
              📚 Documentation
            </button>
          )}
          {!isElectron && (
            <button
              className="config-button"
              onClick={onOpenMetrics}
              title="View Performance Metrics"
            >
              📈 Metrics
            </button>
          )}
          {onSwitchToClassic && (
            <button
              className="config-button"
              onClick={onSwitchToClassic}
              title="Switch to Classic Interface"
              style={{ marginLeft: 'auto', background: 'var(--primary, #4a90e2)' }}
            >
              🔳 Classic
            </button>
          )}
        </div>

        {/* Panel Toggle Controls */}
        <div className="panel-controls">
          <button
            className="panel-toggle-button"
            onClick={handleToggleSidebar}
            title={sidebarCollapsed ? "Show Left Sidebar" : "Hide Left Sidebar"}
          >
            {sidebarCollapsed ? <VscLayoutSidebarLeftOff size={16} /> : <VscLayoutSidebarLeft size={16} />}
          </button>
          <button
            className="panel-toggle-button"
            onClick={handleToggleBottomPanel}
            title={bottomPanelCollapsed ? "Show Bottom Panel" : "Hide Bottom Panel"}
          >
            {bottomPanelCollapsed ? <VscLayoutPanelOff size={16} /> : <VscLayoutPanel size={16} />}
          </button>
          <button
            className="panel-toggle-button"
            onClick={handleToggleRightPanel}
            title="Right Panel (Coming Soon)"
            disabled
            style={{ opacity: 0.4 }}
          >
            {rightPanelCollapsed ? <VscLayoutSidebarRightOff size={16} /> : <VscLayoutSidebarRight size={16} />}
          </button>
        </div>

        {/* Window Controls */}
        <div className="window-controls">
          <button
            className="window-control-button"
            onClick={handleMinimize}
            title="Minimize"
          >
            <VscChromeMinimize size={14} />
          </button>
          <button
            className="window-control-button"
            onClick={handleMaximize}
            title="Maximize"
          >
            <VscChromeMaximize size={14} />
          </button>
          <button
            className="window-control-button window-control-close"
            onClick={handleClose}
            title="Close"
          >
            <VscChromeClose size={14} />
          </button>
        </div>
      </div>

      {/* Workbench Main Area */}
      <div className="workbench-main">
        <PanelGroup direction="horizontal" autoSaveId="benchmesh-layout">
          {/* Activity Bar - Fixed width, always visible */}
          <Panel defaultSize={4} minSize={4} maxSize={4} order={1}>
            <ActivityBar
              instruments={instruments}
              registry={registry}
              activeInstruments={activeInstruments}
              activeView={activeView}
              onInstrumentClick={handleInstrumentClick}
              onViewChange={handleViewChange}
            />
          </Panel>

          {/* Sidebar - Collapsible */}
          {!sidebarCollapsed && (
            <>
              <PanelResizeHandle />
              <Panel defaultSize={20} minSize={15} maxSize={40} order={2}>
                <Sidebar
                  activeView={activeView}
                  instruments={instruments}
                  registry={registry}
                  onClose={handleToggleSidebar}
                />
              </Panel>
            </>
          )}

          {/* Editor + Bottom Panel */}
          <PanelResizeHandle />
          <Panel minSize={30} order={3}>
            <PanelGroup direction="vertical" autoSaveId="benchmesh-editor-panel">
              {/* Editor Area */}
              <Panel defaultSize={70} minSize={30}>
                <EditorArea
                  activeInstruments={activeInstruments}
                  instruments={instruments}
                  registry={registry}
                  onCloseInstrument={(id) => setActiveInstruments((prev) => prev.filter((i) => i !== id))}
                />
              </Panel>

              {/* Bottom Panel - Collapsible */}
              {!bottomPanelCollapsed && (
                <>
                  <PanelResizeHandle />
                  <Panel defaultSize={30} minSize={15} maxSize={50}>
                    <BottomPanel
                      instruments={instruments}
                      registry={registry}
                      onClose={handleToggleBottomPanel}
                    />
                  </Panel>
                </>
              )}
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </div>

      {/* Status Bar - Fixed height, always visible */}
      <StatusBar
        instruments={instruments}
        registry={registry}
        wsDiag={wsDiag}
        apiOk={apiOk}
        apiError={error}
        onToggleSidebar={handleToggleSidebar}
        onToggleBottomPanel={handleToggleBottomPanel}
      />
    </div>
  );
};
