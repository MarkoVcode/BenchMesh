/**
 * MosaicInstrumentWindow - Wrapper for instrument panels in Mosaic
 *
 * Wraps existing InstrumentPod components to work within react-mosaic
 */

import React, { useEffect, useState } from 'react';
import { MosaicWindow, MosaicBranch } from 'react-mosaic-component';
import { VscClose, VscChevronDown, VscChevronUp } from 'react-icons/vsc';
import { ChannelPod } from '../../ClassPods';
import { getClassDescription } from '../../instrumentClasses';
import './editor.css';

interface MosaicInstrumentWindowProps {
  id: string;
  instrument: any;
  classCode?: string; // Specific class to display (for multi-class instruments)
  registry: any;
  path: MosaicBranch[];
  onClose: () => void;
}

export const MosaicInstrumentWindow: React.FC<MosaicInstrumentWindowProps> = ({
  id,
  instrument,
  classCode,
  registry,
  path,
  onClose,
}) => {
  const [classFeatures, setClassFeatures] = useState<Record<string, any>>({});
  const [collapsedChannels, setCollapsedChannels] = useState<Set<string>>(new Set());
  const apiBase = `${window.location.protocol}//${window.location.hostname}:57666`;

  // Get IDN from registry
  const idn = instrument.IDN || registry?.[instrument.id]?.IDN || '—';

  // Get instrument class description for title
  const instrumentName = instrument.name || instrument.id;

  // Determine which classes to display
  const classesToDisplay = classCode
    ? instrument.classes?.filter((c: any) => c.class === classCode) || []
    : instrument.classes || [];

  // Fetch features for each class
  useEffect(() => {
    let cancelled = false;

    async function loadFeaturesForClasses() {
      const features: Record<string, any> = {};

      for (const c of classesToDisplay) {
        try {
          const response = await fetch(`${apiBase}/instruments/${c.class}/${instrument.id}`);
          if (!cancelled && response.ok) {
            const data = await response.json();
            features[c.class] = data;
          }
        } catch (error) {
          console.error(`Failed to fetch features for ${c.class}/${instrument.id}:`, error);
        }
      }

      if (!cancelled) {
        setClassFeatures(features);
      }
    }

    if (classesToDisplay.length > 0) {
      loadFeaturesForClasses();
    }

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, instrument.id, classCode]);

  // Use the first class for the description (or the specified class)
  const displayClassCode = classCode || instrument.classes?.[0]?.class || '';
  const classDescription = displayClassCode ? getClassDescription(displayClassCode) : '';

  // Build resource path (instrument level, not channel level)
  const resourcePathDisplay = classesToDisplay.length > 0
    ? `/instruments/${classesToDisplay[0].class}/${instrument.id}`
    : '';

  // Toggle channel collapse state
  const toggleChannelCollapse = (channelPath: string) => {
    setCollapsedChannels(prev => {
      const newSet = new Set(prev);

      // Calculate total number of channels across all classes
      const totalChannels = classesToDisplay.reduce((sum: number, c: any) => sum + c.channels.length, 0);

      if (newSet.has(channelPath)) {
        // Expanding - always allow
        newSet.delete(channelPath);
      } else {
        // Collapsing - prevent if this is the last expanded channel
        if (newSet.size >= totalChannels - 1) {
          // Would collapse all channels - prevent this
          return prev;
        }
        newSet.add(channelPath);
      }
      return newSet;
    });
  };

  const renderInstrumentContent = () => {
    return (
      <div className="mosaic-instrument__content">
        <div className="mosaic-instrument__body">
          {classesToDisplay.map((c: any, idx: number) => {
            // Get channel colors from fetched features, fallback to gray
            const features = classFeatures[c.class] || {};
            const channelColors = features.channel_colors || {};
            const hasMultipleChannels = c.channels.length > 1;

            return (
              <div key={idx} className="mosaic-instrument__class-section">
                <div className="channels-grid">
                  {c.channels.map((channelPath: string) => {
                    // Extract channel number from path like /instruments/PSU/instrument-1/1
                    const parts = channelPath.split('/');
                    const channelNum = parts[parts.length - 1];
                    const channelResourcePath = `/instruments/${c.class}/${instrument.id}/${channelNum}`;
                    const channelColor = channelColors[channelNum] || '#808080'; // Gray fallback
                    const isCollapsed = collapsedChannels.has(channelPath);

                    // Calculate if this is the last expanded channel
                    const totalChannels = classesToDisplay.reduce((sum: number, cls: any) => sum + cls.channels.length, 0);
                    const isLastExpanded = !isCollapsed && collapsedChannels.size >= totalChannels - 1;

                    return (
                      <div
                        key={channelPath}
                        className={`channel-column ${isCollapsed ? 'channel-column--collapsed' : ''}`}
                      >
                        <div className="channel-subheader">
                          <div className="channel-subheader-content">
                            <div className="channel-label" style={{ color: channelColor }}>
                              CHANNEL {channelNum}
                            </div>
                            <div className="channel-resource-path" title={channelResourcePath}>
                              {channelResourcePath}
                            </div>
                          </div>
                          {hasMultipleChannels && (
                            <button
                              className="channel-collapse-toggle"
                              onClick={() => toggleChannelCollapse(channelPath)}
                              disabled={isLastExpanded}
                              title={
                                isCollapsed
                                  ? 'Expand channel'
                                  : isLastExpanded
                                  ? 'Cannot collapse last channel'
                                  : 'Collapse channel'
                              }
                            >
                              {isCollapsed ? <VscChevronDown size={16} /> : <VscChevronUp size={16} />}
                            </button>
                          )}
                        </div>
                        {!isCollapsed && (
                          <ChannelPod
                            path={channelPath}
                            klass={c.class}
                            uiComponent={c.ui_component}
                            registry={registry}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
        <div className="mosaic-instrument__footer" title={idn}>
          {idn}
        </div>
      </div>
    );
  };

  return (
    <div className="mosaic-instrument-wrapper">
      {resourcePathDisplay && (
        <div className="instrument-resource-path" title={resourcePathDisplay}>
          {resourcePathDisplay}
        </div>
      )}
      {classDescription && (
        <div className="instrument-class-overlay" title={classDescription}>
          {classDescription}
        </div>
      )}
      <MosaicWindow<string>
        path={path}
        title={instrumentName}
        createNode={() => id}
        toolbarControls={[
          <button
            key="close"
            className="mosaic-instrument__close"
            onClick={onClose}
            title="Close"
          >
            <VscClose size={16} />
          </button>,
        ]}
      >
        {renderInstrumentContent()}
      </MosaicWindow>
    </div>
  );
};
