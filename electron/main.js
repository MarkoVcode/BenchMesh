const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const kill = require('tree-kill')

let mainWindow
let backendProcess
let nodeRedProcess

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, 'assets/icon.png')
  })

  // Check if running in development or production
  const isDev = process.env.NODE_ENV === 'development'

  if (isDev) {
    // In development, connect to the running dev server
    mainWindow.loadURL('http://localhost:57666')
    mainWindow.webContents.openDevTools()
  } else {
    // In production, serve the built files
    mainWindow.loadFile(path.join(__dirname, '../benchmesh-serial-service/frontend/dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startBackend() {
  const isDev = process.env.NODE_ENV === 'development'
  const projectRoot = path.join(__dirname, '..')

  if (isDev) {
    console.log('Running in development mode - backend should be started manually with ./start.sh')
    return
  }

  // Start Python backend
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3'
  const backendDir = path.join(projectRoot, 'benchmesh-serial-service')

  backendProcess = spawn(pythonPath, [
    '-m', 'uvicorn',
    'benchmesh_service.api:app',
    '--host', '0.0.0.0',
    '--port', '57666'
  ], {
    cwd: backendDir,
    env: { ...process.env, PYTHONPATH: 'src' },
    stdio: 'inherit'
  })

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err)
  })

  backendProcess.on('exit', (code) => {
    console.log(`Backend process exited with code ${code}`)
  })
}

function startNodeRed() {
  const isDev = process.env.NODE_ENV === 'development'
  const projectRoot = path.join(__dirname, '..')

  if (isDev) {
    console.log('Running in development mode - Node-RED should be started manually with ./start.sh')
    return
  }

  // Start Node-RED
  const nodeRedPath = path.join(projectRoot, 'node_modules/.bin/node-red')
  const nodeRedDir = path.join(projectRoot, '.node-red')

  nodeRedProcess = spawn(nodeRedPath, [
    '--userDir', nodeRedDir,
    '--port', '1880'
  ], {
    cwd: projectRoot,
    stdio: 'inherit'
  })

  nodeRedProcess.on('error', (err) => {
    console.error('Failed to start Node-RED:', err)
  })

  nodeRedProcess.on('exit', (code) => {
    console.log(`Node-RED process exited with code ${code}`)
  })
}

function stopProcesses() {
  return new Promise((resolve) => {
    let killed = 0
    const total = 2

    const checkDone = () => {
      killed++
      if (killed >= total) resolve()
    }

    if (backendProcess) {
      kill(backendProcess.pid, 'SIGTERM', (err) => {
        if (err) console.error('Error killing backend:', err)
        checkDone()
      })
    } else {
      checkDone()
    }

    if (nodeRedProcess) {
      kill(nodeRedProcess.pid, 'SIGTERM', (err) => {
        if (err) console.error('Error killing Node-RED:', err)
        checkDone()
      })
    } else {
      checkDone()
    }
  })
}

app.whenReady().then(() => {
  startBackend()

  // Give backend a moment to start before starting Node-RED
  setTimeout(() => {
    startNodeRed()

    // Give services a moment to start before opening window
    setTimeout(() => {
      createWindow()
    }, 2000)
  }, 1000)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', async () => {
  await stopProcesses()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', async (event) => {
  event.preventDefault()
  await stopProcesses()
  app.exit(0)
})

// Handle IPC messages if needed
ipcMain.on('restart-services', async () => {
  await stopProcesses()
  startBackend()
  setTimeout(startNodeRed, 1000)
})
