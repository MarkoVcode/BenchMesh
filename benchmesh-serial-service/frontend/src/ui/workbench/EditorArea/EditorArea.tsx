/**
 * EditorArea - Multi-panel editor using react-mosaic
 *
 * Allows multiple instruments to be displayed side-by-side with drag-to-split functionality
 */

import React from 'react';
import {
  Mosaic,
  MosaicWindow,
  MosaicBranch,
  MosaicNode,
} from 'react-mosaic-component';
import 'react-mosaic-component/react-mosaic-component.css';
import { MosaicInstrumentWindow } from './MosaicInstrumentWindow';
import './editor.css';

interface EditorAreaProps {
  activeInstruments: string[];
  instruments?: any[];
  registry?: any;
  onCloseInstrument: (id: string) => void;
}

export const EditorArea: React.FC<EditorAreaProps> = ({
  activeInstruments,
  instruments = [],
  registry = {},
  onCloseInstrument,
}) => {
  const [mosaicLayout, setMosaicLayout] = React.useState<MosaicNode<string> | null>(null);

  // Update mosaic layout when active instruments change
  React.useEffect(() => {
    if (activeInstruments.length === 0) {
      setMosaicLayout(null);
      return;
    }

    if (activeInstruments.length === 1) {
      setMosaicLayout(activeInstruments[0]);
      return;
    }

    // Build a simple row layout for multiple instruments
    const buildLayout = (ids: string[]): MosaicNode<string> => {
      if (ids.length === 1) return ids[0];
      if (ids.length === 2) {
        return {
          direction: 'row',
          first: ids[0],
          second: ids[1],
        };
      }

      // For 3+ instruments, create nested layout
      const [first, ...rest] = ids;
      return {
        direction: 'row',
        first,
        second: buildLayout(rest),
        splitPercentage: 100 / ids.length,
      };
    };

    setMosaicLayout(buildLayout(activeInstruments));
  }, [activeInstruments]);

  const renderTile = (id: string, path: MosaicBranch[]) => {
    // Parse class-specific ID format: ${instrument.id}:${classCode}
    const [instrumentId, classCode] = id.includes(':') ? id.split(':') : [id, undefined];

    const instrument = instruments.find((i) => i.id === instrumentId);
    if (!instrument) {
      return <div className="editor__error">Instrument not found: {id}</div>;
    }

    return (
      <MosaicInstrumentWindow
        id={id}
        instrument={instrument}
        classCode={classCode}
        registry={registry}
        path={path}
        onClose={() => onCloseInstrument(id)}
      />
    );
  };

  if (activeInstruments.length === 0 || !mosaicLayout) {
    return (
      <div className="editor editor--empty" data-testid="editor-empty-state">
        <div className="editor__empty-content">
          <div className="editor__empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h3 className="editor__empty-title">No Instrument Selected</h3>
          <p className="editor__empty-description">
            Click an instrument icon in the Activity Bar to open it here
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="editor" data-testid="editor-area">
      <Mosaic<string>
        renderTile={renderTile}
        value={mosaicLayout}
        onChange={setMosaicLayout}
        className="editor__mosaic"
      />
    </div>
  );
};
