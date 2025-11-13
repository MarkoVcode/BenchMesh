import React from 'react'
import { InstrumentPod, Instrument } from './InstrumentPod'
import { MeasurementStatusBar } from './MeasurementStatusBar'

interface ClassicLayoutProps {
  instruments: Instrument[]
  registry: any
  apiBase: string
  loading: boolean
  error: string | null
  wsDiag: { ok: boolean, msg: string, last: number | null }
  onOpenConfig: () => void
  onOpenRecording: () => void
  onOpenDocs: () => void
  onOpenMetrics: () => void
  onSwitchToWorkbench: () => void
  isElectron: boolean
}

export function ClassicLayout({
  instruments,
  registry,
  loading,
  error,
  wsDiag,
  onOpenConfig,
  onOpenRecording,
  onOpenDocs,
  onOpenMetrics,
  onSwitchToWorkbench,
  isElectron
}: ClassicLayoutProps) {
  const apiOk = !loading && !error
  const hasInstruments = instruments && instruments.length > 0

  return (
    <div style={{ paddingBottom: '48px' }}>
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
          {/* Hide Documentation button in Electron (accessible via Help menu) */}
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
          <button
            className="config-button"
            onClick={onSwitchToWorkbench}
            title="Switch to Workbench Interface"
            style={{ marginLeft: 'auto', background: 'var(--primary, #4a90e2)' }}
          >
            🔲 Workbench
          </button>
        </div>
        <div className="statusbar">
          <div className="statuspill" title="WebSocket data flow">
            <span className="dot" style={{ background: wsDiag.ok ? 'var(--good)' : 'var(--bad)' }} />
            <span>{wsDiag.msg}</span>
          </div>
          <div className="statuspill" title="API connectivity">
            <span className="dot" style={{ background: apiOk ? 'var(--good)' : 'var(--bad)' }} />
            <span>{apiOk ? 'API ok' : error ? 'API unreachable' : 'Loading...'}</span>
          </div>
        </div>
      </div>

      {hasInstruments && instruments && (
        <div className="container">
          <div className="grid">
            {instruments.map((ins) => (
              <InstrumentPod key={ins.id} instrument={ins} registry={registry} />
            ))}
          </div>
        </div>
      )}

      <MeasurementStatusBar />
    </div>
  )
}
