import React, { useState } from 'react';
import { Instrument } from '../InstrumentPod';
import { RecordingControls } from './RecordingControls';
import { RecordingList } from './RecordingList';
import { RecordingDetails } from './RecordingDetails';

interface RecordingModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiBase: string;
  instruments: Instrument[];
}

export const RecordingModal: React.FC<RecordingModalProps> = ({
  isOpen,
  onClose,
  apiBase,
  instruments
}) => {
  const [activeTab, setActiveTab] = useState<'new' | 'list'>('new');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [viewingSeriesId, setViewingSeriesId] = useState<number | null>(null);

  if (!isOpen) return null;

  const handleRecordingStarted = (seriesId: number) => {
    console.log('[RecordingModal] Recording started:', seriesId);
    setRefreshTrigger(prev => prev + 1);
    setActiveTab('list');
  };

  const handleViewDetails = (seriesId: number) => {
    setViewingSeriesId(seriesId);
  };

  const handleCloseDetails = () => {
    setViewingSeriesId(null);
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <>
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999,
          padding: '20px'
        }}
        onClick={onClose}
      >
        <div
          style={{
            background: 'white',
            borderRadius: '8px',
            maxWidth: '900px',
            width: '100%',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            style={{
              padding: '20px',
              borderBottom: '2px solid #d9d9d9',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: '#fafafa'
            }}
          >
            <h2 style={{ margin: 0 }}>📊 Data Recording</h2>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                fontSize: '28px',
                cursor: 'pointer',
                padding: '0',
                width: '32px',
                height: '32px',
                lineHeight: '28px'
              }}
            >
              ×
            </button>
          </div>

          {/* Tabs */}
          <div
            style={{
              display: 'flex',
              borderBottom: '1px solid #d9d9d9',
              background: '#fafafa'
            }}
          >
            <button
              onClick={() => setActiveTab('new')}
              style={{
                flex: 1,
                padding: '12px',
                background: activeTab === 'new' ? 'white' : 'transparent',
                border: 'none',
                borderBottom: activeTab === 'new' ? '2px solid #1890ff' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '15px',
                fontWeight: activeTab === 'new' ? 'bold' : 'normal',
                color: activeTab === 'new' ? '#1890ff' : '#666'
              }}
            >
              🔴 New Recording
            </button>
            <button
              onClick={() => setActiveTab('list')}
              style={{
                flex: 1,
                padding: '12px',
                background: activeTab === 'list' ? 'white' : 'transparent',
                border: 'none',
                borderBottom: activeTab === 'list' ? '2px solid #1890ff' : '2px solid transparent',
                cursor: 'pointer',
                fontSize: '15px',
                fontWeight: activeTab === 'list' ? 'bold' : 'normal',
                color: activeTab === 'list' ? '#1890ff' : '#666'
              }}
            >
              📋 All Recordings
            </button>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {activeTab === 'new' && (
              <RecordingControls
                apiBase={apiBase}
                instruments={instruments}
                onRecordingStarted={handleRecordingStarted}
              />
            )}
            {activeTab === 'list' && (
              <RecordingList
                apiBase={apiBase}
                onViewDetails={handleViewDetails}
                refreshTrigger={refreshTrigger}
              />
            )}
          </div>

          {/* Footer */}
          <div
            style={{
              padding: '15px 20px',
              borderTop: '1px solid #d9d9d9',
              background: '#fafafa',
              textAlign: 'right'
            }}
          >
            <button
              onClick={onClose}
              style={{
                padding: '10px 24px',
                background: '#d9d9d9',
                color: '#333',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 'bold'
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>

      {/* Recording Details Modal */}
      {viewingSeriesId !== null && (
        <RecordingDetails
          seriesId={viewingSeriesId}
          apiBase={apiBase}
          onClose={handleCloseDetails}
        />
      )}
    </>
  );
};
