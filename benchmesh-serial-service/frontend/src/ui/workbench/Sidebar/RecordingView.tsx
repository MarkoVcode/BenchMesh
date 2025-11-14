/**
 * RecordingView - Recording management with tabs
 *
 * Provides two views:
 * - New Recording: Create and configure new recordings
 * - All Recordings: Browse and manage existing recordings
 */

import React, { useState } from 'react';
import { VscCircleFilled, VscHistory } from 'react-icons/vsc';

type RecordingTab = 'new' | 'all';

export const RecordingView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<RecordingTab>('new');

  return (
    <div className="recording-view">
      <div className="recording-view__tabs">
        <button
          className={`recording-view__tab ${activeTab === 'new' ? 'recording-view__tab--active' : ''}`}
          onClick={() => setActiveTab('new')}
        >
          <VscCircleFilled size={14} />
          <span>New Recording</span>
        </button>
        <button
          className={`recording-view__tab ${activeTab === 'all' ? 'recording-view__tab--active' : ''}`}
          onClick={() => setActiveTab('all')}
        >
          <VscHistory size={14} />
          <span>All Recordings</span>
        </button>
      </div>

      <div className="recording-view__content">
        {activeTab === 'new' && (
          <div className="recording-view__new">
            <div className="recording-view__section">
              <h3 className="recording-view__section-title">Recording Configuration</h3>
              <div className="recording-view__form">
                <div className="recording-view__field">
                  <label className="recording-view__label">Recording Name</label>
                  <input
                    type="text"
                    className="recording-view__input"
                    placeholder="Enter recording name..."
                  />
                </div>

                <div className="recording-view__field">
                  <label className="recording-view__label">Sample Interval (ms)</label>
                  <input
                    type="number"
                    className="recording-view__input"
                    placeholder="1000"
                    min="10"
                  />
                </div>

                <div className="recording-view__field">
                  <label className="recording-view__label">Duration</label>
                  <select className="recording-view__select">
                    <option>Continuous</option>
                    <option>1 minute</option>
                    <option>5 minutes</option>
                    <option>15 minutes</option>
                    <option>30 minutes</option>
                    <option>1 hour</option>
                  </select>
                </div>

                <div className="recording-view__field">
                  <label className="recording-view__label">Instruments</label>
                  <div className="recording-view__placeholder-text">
                    Select instruments to record...
                  </div>
                </div>
              </div>

              <div className="recording-view__actions">
                <button className="recording-view__button recording-view__button--primary">
                  <VscCircleFilled size={14} />
                  Start Recording
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'all' && (
          <div className="recording-view__all">
            <div className="recording-view__list">
              <div className="recording-view__empty">
                <VscHistory size={48} />
                <p>No recordings found</p>
                <span className="recording-view__hint">
                  Start a new recording to begin capturing instrument data
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
