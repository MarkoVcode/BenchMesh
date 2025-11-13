/**
 * ActivityBar - Vertical ribbon with instrument/view icons
 *
 * Left-aligned vertical bar showing:
 * - Instrument icons with LED status badges
 * - View icons (settings, recording, metrics)
 */

import React from 'react';
import { ActivityBarItem } from './ActivityBarItem';
import { getInstrumentIcon, getViewIcon } from '../icons';
import { HealthStatus } from './LEDBadge';
import { ViewType } from '../WorkbenchLayout';
import './activity-bar.css';

interface ActivityBarProps {
  instruments?: any[];
  registry?: any;
  activeInstruments: string[];
  activeView: ViewType;
  onInstrumentClick: (id: string) => void;
  onViewChange: (view: ViewType) => void;
}

export const ActivityBar: React.FC<ActivityBarProps> = ({
  instruments = [],
  registry = {},
  activeInstruments,
  activeView,
  onInstrumentClick,
  onViewChange,
}) => {
  const getHealthStatus = (deviceId: string): HealthStatus | undefined => {
    const deviceData = registry[deviceId];
    if (!deviceData) return undefined;

    // Check if device has IDN (connected)
    const hasIDN = deviceData.IDN && String(deviceData.IDN).trim().length > 0;

    // Connected: show amber indicator
    // Disconnected: no indicator (return undefined)
    return hasIDN ? 'degraded' : undefined;
  };

  return (
    <div className="activity-bar" data-testid="activity-bar">
      <div className="activity-bar__instruments">
        {instruments.map((instrument) => {
          const classes = instrument.classes || [];
          const hasMultipleClasses = classes.length > 1;
          const healthStatus = getHealthStatus(instrument.id);

          // For single-class instruments, render as before (clickable)
          if (!hasMultipleClasses && classes.length === 1) {
            const classCode = classes[0].class;
            const Icon = getInstrumentIcon(classCode);
            const classId = `${instrument.id}:${classCode}`;
            const isActive = activeInstruments.includes(classId);

            return (
              <ActivityBarItem
                key={classId}
                id={classId}
                icon={Icon}
                label={instrument.name || instrument.id}
                active={isActive}
                healthStatus={healthStatus}
                onClick={() => onInstrumentClick(classId)}
              />
            );
          }

          // For multi-class instruments, render parent (non-clickable) + children (clickable)
          if (hasMultipleClasses) {
            // Get icon from first class for parent
            const ParentIcon = getInstrumentIcon(classes[0]?.class || '');

            return (
              <React.Fragment key={instrument.id}>
                {/* Parent item - non-clickable, shows connection status */}
                <ActivityBarItem
                  id={instrument.id}
                  icon={ParentIcon}
                  label={instrument.name || instrument.id}
                  active={false}
                  healthStatus={healthStatus}
                  onClick={() => {}} // Non-clickable
                  isParent={true}
                />

                {/* Child items - clickable, one per class */}
                {classes.map((classInfo: any) => {
                  const classCode = classInfo.class;
                  const Icon = getInstrumentIcon(classCode);
                  const classId = `${instrument.id}:${classCode}`;
                  const isActive = activeInstruments.includes(classId);

                  return (
                    <ActivityBarItem
                      key={classId}
                      id={classId}
                      icon={Icon}
                      label={`${instrument.name || instrument.id} - ${classCode}`}
                      active={isActive}
                      onClick={() => onInstrumentClick(classId)}
                      isChild={true}
                    />
                  );
                })}
              </React.Fragment>
            );
          }

          return null;
        })}
      </div>

      <div className="activity-bar__separator" />

      <div className="activity-bar__views">
        <ActivityBarItem
          id="settings"
          icon={getViewIcon('settings')}
          label="Settings"
          active={activeView === 'settings'}
          onClick={() => onViewChange('settings')}
        />
        <ActivityBarItem
          id="recording"
          icon={getViewIcon('recording')}
          label="Recording"
          active={activeView === 'recording'}
          onClick={() => onViewChange('recording')}
        />
        <ActivityBarItem
          id="metrics"
          icon={getViewIcon('metrics')}
          label="Metrics"
          active={activeView === 'metrics'}
          onClick={() => onViewChange('metrics')}
        />
      </div>
    </div>
  );
};
