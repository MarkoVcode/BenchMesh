/**
 * NodeRedPanel - Embedded Node-RED editor in iframe
 *
 * Features:
 * - Lazy-loaded iframe (only renders when tab is active)
 * - Loading state with spinner
 * - Error handling for connection failures
 * - "Open in new window" button for external access
 */

import React, { useState } from 'react';
import { VscLinkExternal } from 'react-icons/vsc';
import './node-red-panel.css';

export const NodeRedPanel: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const nodeRedUrl = `http://${window.location.hostname}:1880/`;

  const handleIframeLoad = () => {
    setLoading(false);
    setError(false);
  };

  const handleIframeError = () => {
    setLoading(false);
    setError(true);
  };

  const handleOpenExternal = () => {
    window.open(nodeRedUrl, '_blank');
  };

  return (
    <div className="node-red-panel" data-testid="node-red-panel">
      {/* Toolbar with external window button */}
      <div className="node-red-panel__toolbar">
        <button
          className="node-red-panel__external-button"
          onClick={handleOpenExternal}
          title="Open Node-RED in new window"
        >
          <VscLinkExternal size={16} />
          <span>Open Node-RED in new window</span>
        </button>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="node-red-panel__loading">
          <div className="node-red-panel__spinner" />
          <p>Loading automation editor...</p>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="node-red-panel__error">
          <p>Failed to load Node-RED. Is the Node-RED service running?</p>
          <button onClick={handleOpenExternal}>Try opening in new window</button>
        </div>
      )}

      {/* Embedded iframe */}
      <iframe
        src={nodeRedUrl}
        title="Node-RED Editor"
        className="node-red-panel__iframe"
        onLoad={handleIframeLoad}
        onError={handleIframeError}
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
        style={{ display: loading || error ? 'none' : 'block' }}
      />
    </div>
  );
};
