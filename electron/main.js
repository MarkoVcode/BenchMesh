const { app, BrowserWindow, ipcMain, Menu, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const kill = require('tree-kill')
const fs = require('fs')
const { initializeUserData } = require('./init-user-data')
const { checkVersionDowngrade, saveVersionToUserData } = require('./version-manager')

let mainWindow
let backendProcess
let nodeRedProcess
let aboutWindow = null
let docsWindow = null
let userDocsWindow = null
let metricsWindow = null
let isQuitting = false  // Track if we're in shutdown sequence

// Load version information
const versionPath = path.join(__dirname, '..', 'version.json')
const versionInfo = JSON.parse(fs.readFileSync(versionPath, 'utf8'))

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'BenchMesh',
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
    // In production, load the backend URL which serves the UI
    mainWindow.loadURL('http://localhost:57666/ui/')
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Create application menu
  createMenu()
}

function createAboutWindow() {
  if (aboutWindow) {
    aboutWindow.focus()
    return
  }

  aboutWindow = new BrowserWindow({
    width: 400,
    height: 300,
    title: 'About BenchMesh',
    resizable: false,
    minimizable: false,
    maximizable: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    parent: mainWindow,
    modal: true
  })

  // Create HTML content for About window
  const logoPath = path.join(__dirname, '..', 'docs', 'static', 'BenchMesh.png')
  const aboutHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>About BenchMesh</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      margin: 0;
      padding: 20px;
      text-align: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: calc(100vh - 40px);
    }
    img {
      width: 50%;
      height: auto;
      margin-bottom: 20px;
      filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.3));
    }
    h1 {
      margin: 10px 0;
      font-size: 24px;
      font-weight: 600;
    }
    p {
      margin: 5px 0;
      font-size: 14px;
      opacity: 0.9;
    }
    .version {
      font-size: 16px;
      font-weight: 500;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <img src="file://${logoPath}" alt="BenchMesh Logo">
  <h1>${versionInfo.name}</h1>
  <p>${versionInfo.description}</p>
  <p class="version">Version ${versionInfo.version}</p>
</body>
</html>
  `

  aboutWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(aboutHtml)}`)

  aboutWindow.on('closed', () => {
    aboutWindow = null
  })
}

function createDocsWindow() {
  if (docsWindow) {
    docsWindow.focus()
    return
  }

  // Calculate window size (10% smaller than main window, or default if main is too small)
  let width = 1400
  let height = 900

  if (mainWindow) {
    const mainBounds = mainWindow.getBounds()
    if (mainBounds.width > 800 && mainBounds.height > 600) {
      width = Math.floor(mainBounds.width * 0.9)
      height = Math.floor(mainBounds.height * 0.9)
    }
  }

  docsWindow = new BrowserWindow({
    width,
    height,
    title: 'BenchMesh API Documentation',
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    parent: mainWindow
  })

  const isDev = process.env.NODE_ENV === 'development'

  if (isDev) {
    docsWindow.loadURL('http://localhost:57666/docs')
  } else {
    docsWindow.loadURL('http://localhost:57666/docs')
  }

  docsWindow.on('closed', () => {
    docsWindow = null
  })
}

function createUserDocsWindow() {
  if (userDocsWindow) {
    userDocsWindow.focus()
    return
  }

  // Calculate window size (10% smaller than main window, or default if main is too small)
  let width = 1400
  let height = 900

  if (mainWindow) {
    const mainBounds = mainWindow.getBounds()
    if (mainBounds.width > 800 && mainBounds.height > 600) {
      width = Math.floor(mainBounds.width * 0.9)
      height = Math.floor(mainBounds.height * 0.9)
    }
  }

  userDocsWindow = new BrowserWindow({
    width,
    height,
    title: 'BenchMesh Documentation',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    parent: mainWindow
  })

  const isDev = process.env.NODE_ENV === 'development'

  if (isDev) {
    userDocsWindow.loadURL('http://localhost:57666/ui/docs')
  } else {
    userDocsWindow.loadURL('http://localhost:57666/ui/docs')
  }

  userDocsWindow.on('closed', () => {
    userDocsWindow = null
  })
}

function createMetricsWindow() {
  if (metricsWindow) {
    metricsWindow.focus()
    return
  }

  // Calculate window size (10% smaller than main window, or default if main is too small)
  let width = 1400
  let height = 900

  if (mainWindow) {
    const mainBounds = mainWindow.getBounds()
    if (mainBounds.width > 800 && mainBounds.height > 600) {
      width = Math.floor(mainBounds.width * 0.9)
      height = Math.floor(mainBounds.height * 0.9)
    }
  }

  metricsWindow = new BrowserWindow({
    width,
    height,
    title: 'BenchMesh Metrics',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    parent: mainWindow
  })

  const isDev = process.env.NODE_ENV === 'development'

  if (isDev) {
    metricsWindow.loadURL('http://localhost:57666/ui/metrics')
  } else {
    metricsWindow.loadURL('http://localhost:57666/ui/metrics')
  }

  metricsWindow.on('closed', () => {
    metricsWindow = null
  })
}

function createMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit()
          }
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'close' }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Documentation',
          click: () => {
            createUserDocsWindow()
          }
        },
        {
          label: 'API Documentation',
          click: () => {
            createDocsWindow()
          }
        },
        {
          label: 'Metrics',
          click: () => {
            createMetricsWindow()
          }
        },
        {
          type: 'separator'
        },
        {
          label: 'About BenchMesh',
          click: () => {
            createAboutWindow()
          }
        }
      ]
    }
  ]

  // On macOS, add app menu as first item
  if (process.platform === 'darwin') {
    template.unshift({
      label: app.name,
      submenu: [
        {
          label: `About ${app.name}`,
          click: () => {
            createAboutWindow()
          }
        },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    })
  }

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

async function showVersionDowngradeWarning(currentVersion, lastVersion) {
  const result = await dialog.showMessageBox({
    type: 'warning',
    title: 'Version Downgrade Detected',
    message: 'Running an older version of BenchMesh',
    detail: `You are about to run version ${currentVersion.version}, but you previously used version ${lastVersion.version}.\n\n` +
            'Running an older version may result in:\n' +
            '• Data corruption\n' +
            '• Incompatible configuration formats\n' +
            '• Unexpected application behavior\n\n' +
            'It is recommended to use the latest version or perform a fresh installation.\n\n' +
            'Do you want to continue anyway?',
    buttons: ['Exit Application', 'Continue Anyway'],
    defaultId: 0,
    cancelId: 0
  })

  return result.response === 1 // Returns true if "Continue Anyway" was clicked
}

function startBackend(userDataPaths) {
  const isDev = process.env.NODE_ENV === 'development'
  const projectRoot = path.join(__dirname, '..')

  if (isDev) {
    console.log('Running in development mode - backend should be started manually with ./start.sh')
    return
  }

  // Start Python backend
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3'
  const backendDir = path.join(projectRoot, 'benchmesh-serial-service')

  console.log('Starting backend...')
  console.log('Python path:', pythonPath)
  console.log('Backend directory:', backendDir)
  console.log('Project root:', projectRoot)
  console.log('Config path:', userDataPaths.configPath)
  console.log('Data directory:', userDataPaths.userDataDir)

  backendProcess = spawn(pythonPath, [
    '-m', 'uvicorn',
    'benchmesh_service.api:app',
    '--host', '0.0.0.0',
    '--port', '57666'
  ], {
    cwd: backendDir,
    env: {
      ...process.env,
      PYTHONPATH: 'src',
      BENCHMESH_CONFIG: userDataPaths.configPath,
      BENCHMESH_DATA_DIR: userDataPaths.userDataDir
    },
    stdio: ['ignore', 'pipe', 'pipe']
  })

  // Create log streams for backend output
  const backendLogPath = path.join(userDataPaths.logsDir, 'uvicorn.log')
  const backendErrorLogPath = path.join(userDataPaths.logsDir, 'uvicorn_error.log')

  const backendLogStream = fs.createWriteStream(backendLogPath, { flags: 'a' })
  const backendErrorLogStream = fs.createWriteStream(backendErrorLogPath, { flags: 'a' })

  backendProcess.stdout.on('data', (data) => {
    const message = data.toString()
    console.log('[Backend]', message.trim())
    backendLogStream.write(`${new Date().toISOString()} ${message}`)
  })

  backendProcess.stderr.on('data', (data) => {
    const message = data.toString()
    console.error('[Backend Error]', message.trim())
    backendErrorLogStream.write(`${new Date().toISOString()} ${message}`)
  })

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err)
    backendErrorLogStream.write(`${new Date().toISOString()} Failed to start backend: ${err.message}\n`)
  })

  backendProcess.on('exit', (code) => {
    console.log(`Backend process exited with code ${code}`)
    backendLogStream.write(`${new Date().toISOString()} Backend process exited with code ${code}\n`)
    backendLogStream.end()
    backendErrorLogStream.end()
  })
}

function startNodeRed(userDataPaths) {
  const isDev = process.env.NODE_ENV === 'development'
  const projectRoot = path.join(__dirname, '..')

  if (isDev) {
    console.log('Running in development mode - Node-RED should be started manually with ./start.sh')
    return
  }

  // Start Node-RED
  const nodeRedPath = path.join(projectRoot, 'node_modules/.bin/node-red')

  console.log('Starting Node-RED...')
  console.log('Node-RED path:', nodeRedPath)
  console.log('Node-RED user dir:', userDataPaths.nodeRedDir)

  nodeRedProcess = spawn(nodeRedPath, [
    '--userDir', userDataPaths.nodeRedDir,
    '--port', '1880'
  ], {
    cwd: projectRoot,
    stdio: ['ignore', 'pipe', 'pipe']
  })

  // Create log streams for Node-RED output
  const nodeRedLogPath = path.join(userDataPaths.logsDir, 'node-red.log')
  const nodeRedErrorLogPath = path.join(userDataPaths.logsDir, 'node-red_error.log')

  const nodeRedLogStream = fs.createWriteStream(nodeRedLogPath, { flags: 'a' })
  const nodeRedErrorLogStream = fs.createWriteStream(nodeRedErrorLogPath, { flags: 'a' })

  nodeRedProcess.stdout.on('data', (data) => {
    const message = data.toString()
    console.log('[Node-RED]', message.trim())
    nodeRedLogStream.write(`${new Date().toISOString()} ${message}`)
  })

  nodeRedProcess.stderr.on('data', (data) => {
    const message = data.toString()
    console.error('[Node-RED Error]', message.trim())
    nodeRedErrorLogStream.write(`${new Date().toISOString()} ${message}`)
  })

  nodeRedProcess.on('error', (err) => {
    console.error('Failed to start Node-RED:', err)
    nodeRedErrorLogStream.write(`${new Date().toISOString()} Failed to start Node-RED: ${err.message}\n`)
  })

  nodeRedProcess.on('exit', (code) => {
    console.log(`Node-RED process exited with code ${code}`)
    nodeRedLogStream.write(`${new Date().toISOString()} Node-RED process exited with code ${code}\n`)
    nodeRedLogStream.end()
    nodeRedErrorLogStream.end()
  })
}

function stopProcesses() {
  return new Promise((resolve) => {
    let killed = 0
    const total = 2
    let resolved = false

    // Ensure we resolve within 5 seconds even if processes don't stop cleanly
    const timeout = setTimeout(() => {
      if (!resolved) {
        console.warn('Process cleanup timed out after 5s, forcing exit')
        resolved = true
        resolve()
      }
    }, 5000)

    const checkDone = () => {
      killed++
      if (killed >= total && !resolved) {
        resolved = true
        clearTimeout(timeout)
        console.log('All processes stopped cleanly')
        resolve()
      }
    }

    if (backendProcess) {
      console.log(`Stopping backend process (PID: ${backendProcess.pid})`)
      kill(backendProcess.pid, 'SIGTERM', (err) => {
        if (err) console.error('Error killing backend:', err)
        else console.log('Backend process stopped')
        backendProcess = null
        checkDone()
      })
    } else {
      console.log('No backend process to stop')
      checkDone()
    }

    if (nodeRedProcess) {
      console.log(`Stopping Node-RED process (PID: ${nodeRedProcess.pid})`)
      kill(nodeRedProcess.pid, 'SIGTERM', (err) => {
        if (err) console.error('Error killing Node-RED:', err)
        else console.log('Node-RED process stopped')
        nodeRedProcess = null
        checkDone()
      })
    } else {
      console.log('No Node-RED process to stop')
      checkDone()
    }
  })
}

async function waitForBackend(retries = 30, delay = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      const http = require('http')
      const response = await new Promise((resolve, reject) => {
        const req = http.get('http://localhost:57666/instruments', (res) => {
          resolve(res.statusCode === 200)
        })
        req.on('error', () => resolve(false))
        req.setTimeout(2000, () => {
          req.destroy()
          resolve(false)
        })
      })

      if (response) {
        console.log('Backend is ready!')
        // Give it a bit more time to fully initialize
        await new Promise(resolve => setTimeout(resolve, 1000))
        return true
      }
    } catch (err) {
      // Ignore
    }

    console.log(`Waiting for backend... (${i + 1}/${retries})`)
    await new Promise(resolve => setTimeout(resolve, delay))
  }

  console.warn('Backend did not respond in time, continuing anyway...')
  return false
}

app.whenReady().then(async () => {
  // Initialize user data directory structure
  const projectRoot = path.join(__dirname, '..')
  const userDataPaths = initializeUserData(projectRoot)

  // Check for version downgrade
  const versionCheck = checkVersionDowngrade(projectRoot, userDataPaths.userDataDir)

  if (versionCheck.isDowngrade) {
    const continueAnyway = await showVersionDowngradeWarning(
      versionCheck.currentVersion,
      versionCheck.lastVersion
    )

    if (!continueAnyway) {
      console.log('User chose to exit due to version downgrade')
      app.quit()
      return
    }

    console.log('User chose to continue despite version downgrade')
  }

  // Save current version to user data for future comparisons
  if (versionCheck.currentVersion) {
    saveVersionToUserData(userDataPaths.userDataDir, versionCheck.currentVersion)
  }

  startBackend(userDataPaths)

  // Give backend a moment to start before starting Node-RED
  setTimeout(() => {
    startNodeRed(userDataPaths)
  }, 1000)

  // Wait for backend to be ready before opening window
  await waitForBackend()

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', async () => {
  // Don't stop processes here if we're already quitting (handled in before-quit)
  if (!isQuitting) {
    console.log('All windows closed, initiating shutdown...')
    isQuitting = true
    await stopProcesses()
  }

  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', async (event) => {
  // Only stop processes once
  if (!isQuitting) {
    console.log('Application quitting, stopping backend services...')
    isQuitting = true
    event.preventDefault()  // Prevent quit to allow cleanup

    await stopProcesses()

    // Force kill any remaining processes after timeout
    setTimeout(() => {
      console.log('Final cleanup, forcing exit')
      app.exit(0)
    }, 1000)
  }
})

// Handle IPC messages if needed
ipcMain.on('restart-services', async () => {
  await stopProcesses()
  const projectRoot = path.join(__dirname, '..')
  const userDataPaths = initializeUserData(projectRoot)
  startBackend(userDataPaths)
  setTimeout(() => startNodeRed(userDataPaths), 1000)
})
