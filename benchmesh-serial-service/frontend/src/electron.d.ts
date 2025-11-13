/**
 * Type declarations for Electron API exposed via preload script
 */

interface ElectronAPI {
  /** Restart backend and Node-RED services */
  restartServices: () => void
  /** Current platform (darwin, win32, linux) */
  platform: string
  /** Whether running in development mode */
  isDev: boolean
  /** Whether running in Electron wrapper */
  isElectron: boolean
  /** Application version */
  version: string
  /** Application name */
  appName: string
  /** Minimize window */
  minimize?: () => void
  /** Maximize/restore window */
  maximize?: () => void
  /** Close window */
  close?: () => void
}

declare global {
  interface Window {
    electron?: ElectronAPI
  }
}

export {}
