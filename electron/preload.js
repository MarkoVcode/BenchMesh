const { contextBridge, ipcRenderer } = require('electron')

// Load version information with fallback
let versionInfo = { version: '0.0.51', name: 'BenchMesh' }

try {
  const fs = require('fs')
  const path = require('path')
  const versionPath = path.join(__dirname, '..', 'version.json')
  versionInfo = JSON.parse(fs.readFileSync(versionPath, 'utf8'))
} catch (e) {
  console.error('Failed to load version info in preload:', e)
  // Use fallback values defined above
}

// Expose protected methods that allow the renderer process to use
// ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  restartServices: () => ipcRenderer.send('restart-services'),
  platform: process.platform,
  isDev: process.env.NODE_ENV === 'development',
  isElectron: true,
  version: versionInfo.version,
  appName: versionInfo.name
})
