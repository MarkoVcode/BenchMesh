/**
 * LEDBadge - Connection status indicator
 *
 * Shows a colored LED dot indicating instrument health:
 * - Green: healthy/connected
 * - Yellow: degraded
 * - Red: dead/error
 * - Gray: disconnected/unknown
 */

import React from 'react';
import './activity-bar.css';

export type HealthStatus = 'healthy' | 'degraded' | 'dead' | 'unknown';

interface LEDBadgeProps {
  status: HealthStatus;
  className?: string;
}

export const LEDBadge: React.FC<LEDBadgeProps> = ({ status, className = '' }) => {
  return (
    <span className={`led-badge led-badge--${status} ${className}`} />
  );
};
