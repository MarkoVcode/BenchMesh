const { contextBridge, ipcRenderer } = require('electron')

// Expose protected methods that allow the renderer process to use
// ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electron', {
  restartServices: () => ipcRenderer.send('restart-services'),
  platform: process.platform,
  isDev: process.env.NODE_ENV === 'development'
})
