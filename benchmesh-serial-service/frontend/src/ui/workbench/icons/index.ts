/**
 * Icon mapping for instrument classes
 *
 * Maps 3-letter instrument class codes to appropriate VS Code icons
 */

import {
  VscCircuitBoard,
  VscPulse,
  VscSymbolRuler,
  VscBeaker,
  VscGraphLine,
  VscSettings,
  VscFileSubmodule,
  VscGraph,
  VscDatabase,
  VscTools,
} from 'react-icons/vsc';
import { IconType } from 'react-icons';

export type InstrumentClass = 'PSU' | 'DMM' | 'SPM' | 'OSC' | 'OEL' | 'DGE' | 'XDM' | string;

/**
 * Map instrument class codes to icon components
 */
export const instrumentIcons: Record<string, IconType> = {
  PSU: VscCircuitBoard, // Power Supply Unit - circuit board
  DMM: VscSymbolRuler, // Digital Multimeter - measurement tool
  SPM: VscPulse, // Signal/Power Meter - pulse wave
  OSC: VscGraphLine, // Oscilloscope - waveform graph
  OEL: VscBeaker, // Electronic Load - beaker/load
  DGE: VscPulse, // Digital Generator - pulse/signal
  XDM: VscSymbolRuler, // XDM Multimeter - measurement
};

/**
 * View icons for sidebar navigation
 */
export const viewIcons = {
  instruments: VscTools,
  settings: VscSettings,
  recording: VscDatabase,
  metrics: VscGraph,
};

/**
 * Get icon component for an instrument class
 */
export const getInstrumentIcon = (classCode: string): IconType => {
  return instrumentIcons[classCode] || VscFileSubmodule;
};

/**
 * Get icon component for a view
 */
export const getViewIcon = (view: string): IconType => {
  return viewIcons[view as keyof typeof viewIcons] || VscTools;
};
