/**
 * InstrumentListView - Tree view of all configured instruments
 */

import React from 'react';
import { VscCircleFilled } from 'react-icons/vsc';
import { getInstrumentIcon } from '../icons';
import './sidebar.css';

interface InstrumentListViewProps {
  instruments?: any[];
  registry?: any;
}

export const InstrumentListView: React.FC<InstrumentListViewProps> = ({
  instruments = [],
  registry = {},
}) => {
  const getConnectionStatus = (deviceId: string) => {
    const deviceData = registry[deviceId];
    if (!deviceData?.IDN) return 'disconnected';

    const health = deviceData.health_status || 'unknown';
    if (health === 'dead') return 'error';
    if (health === 'degraded') return 'warning';
    if (health === 'healthy') return 'connected';
    return 'unknown';
  };

  return (
    <div className="instrument-list">
      <div className="instrument-list__items">
        {instruments.length === 0 ? (
          <div className="instrument-list__empty">
            <p>No instruments configured</p>
            <p className="instrument-list__hint">
              Click Settings to add instruments
            </p>
          </div>
        ) : (
          instruments.map((instrument) => {
            const Icon = getInstrumentIcon(instrument.class);
            const status = getConnectionStatus(instrument.id);

            return (
              <div
                key={instrument.id}
                className="instrument-list__item"
                data-testid={`instrument-list-item-${instrument.id}`}
              >
                <div className="instrument-list__item-icon">
                  <Icon size={16} />
                </div>
                <div className="instrument-list__item-info">
                  <div className="instrument-list__item-name">
                    {instrument.name || instrument.id}
                  </div>
                  <div className="instrument-list__item-details">
                    {instrument.class} • {instrument.port}
                  </div>
                </div>
                <div className={`instrument-list__item-status instrument-list__item-status--${status}`}>
                  <VscCircleFilled size={8} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
