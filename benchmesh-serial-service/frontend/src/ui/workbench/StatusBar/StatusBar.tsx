/**
 * StatusBar - Footer status bar
 *
 * Shows:
 * - Left: WebSocket status, device connection count
 * - Right: API response time, Node-RED status
 */

import React from 'react';
import { VscCircleFilled, VscDebugDisconnect, VscRadioTower } from 'react-icons/vsc';
import './status-bar.css';

interface StatusBarProps {
  instruments?: any[];
  registry?: any;
  wsDiag?: { ok: boolean; msg: string; last: number | null };
  apiOk?: boolean;
  apiError?: string | null;
  onToggleSidebar: () => void;
  onToggleBottomPanel: () => void;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  instruments = [],
  registry = {},
  wsDiag = { ok: false, msg: 'disconnected', last: null },
  apiOk = false,
  apiError = null,
}) => {
  const connectedCount = instruments.filter((inst) => registry[inst.id]?.IDN).length;
  const totalCount = instruments.length;

  return (
    <div className="status-bar" data-testid="status-bar">
      <div className="status-bar__left">
        <div className="status-bar__item" title="WebSocket data flow">
          <span>WS: {wsDiag.msg}</span>
        </div>

        <div className="status-bar__separator" />

        <div className="status-bar__item" title="API connectivity">
          <span>API: {apiOk ? 'ok' : apiError ? 'unreachable' : 'Loading...'}</span>
        </div>

        <div className="status-bar__separator" />

        <div className="status-bar__item" title="Instrument Connections">
          <VscCircleFilled size={8} style={{ color: connectedCount > 0 ? 'var(--led-connected)' : 'var(--led-disconnected)' }} />
          <span>{connectedCount}/{totalCount} Instruments</span>
        </div>
      </div>

      <div className="status-bar__right">
        <div className="status-bar__item" title="Node-RED Status">
          <span>Node-RED: Running</span>
        </div>
      </div>
    </div>
  );
};
