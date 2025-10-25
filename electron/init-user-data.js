/**
 * User Data Initialization for BenchMesh Electron App
 *
 * Handles creation of persistent user data directory structure
 * and copying of default configuration files.
 *
 * User data is stored in ~/.benchmesh/ to persist across app updates.
 */

const fs = require('fs')
const path = require('path')
const os = require('os')

/**
 * Get the user data directory path
 * @returns {string} Absolute path to ~/.benchmesh/
 */
function getUserDataDir() {
  return path.join(os.homedir(), '.benchmesh')
}

/**
 * Ensure a directory exists, creating it if necessary
 * @param {string} dirPath - Directory path to ensure
 */
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true })
    console.log(`Created directory: ${dirPath}`)
  }
}

/**
 * Copy a file if it doesn't exist at the destination
 * @param {string} sourcePath - Source file path
 * @param {string} destPath - Destination file path
 */
function copyFileIfNotExists(sourcePath, destPath) {
  if (!fs.existsSync(destPath)) {
    // Ensure destination directory exists
    const destDir = path.dirname(destPath)
    ensureDir(destDir)

    // Copy the file
    fs.copyFileSync(sourcePath, destPath)
    console.log(`Copied default file: ${sourcePath} -> ${destPath}`)
  }
}

/**
 * Create a symlink if it doesn't exist
 * @param {string} target - Target path (what the symlink points to)
 * @param {string} linkPath - Symlink path
 */
function createSymlinkIfNotExists(target, linkPath) {
  if (!fs.existsSync(linkPath)) {
    // Ensure parent directory exists
    const linkDir = path.dirname(linkPath)
    ensureDir(linkDir)

    try {
      fs.symlinkSync(target, linkPath, 'dir')
      console.log(`Created symlink: ${linkPath} -> ${target}`)
    } catch (error) {
      console.error(`Failed to create symlink ${linkPath}:`, error.message)
    }
  }
}

/**
 * Initialize user data directory structure
 * Creates ~/.benchmesh/ and subdirectories, copies default config
 *
 * @param {string} projectRoot - Absolute path to project root directory
 * @returns {Object} Object containing paths:
 *   - userDataDir: ~/.benchmesh/
 *   - configPath: ~/.benchmesh/config.yaml
 *   - nodeRedDir: ~/.benchmesh/node-red/
 *   - logsDir: ~/.benchmesh/logs/
 */
function initializeUserData(projectRoot) {
  const userDataDir = getUserDataDir()

  console.log('=========================================')
  console.log('Initializing BenchMesh User Data')
  console.log('=========================================')
  console.log(`User data directory: ${userDataDir}`)
  console.log(`Project root: ${projectRoot}`)

  // Create main user data directory
  ensureDir(userDataDir)

  // Create subdirectories
  const nodeRedDir = path.join(userDataDir, 'node-red')
  const logsDir = path.join(userDataDir, 'logs')

  ensureDir(nodeRedDir)
  ensureDir(logsDir)

  // Copy default config.yaml if it doesn't exist
  const sourceConfig = path.join(projectRoot, 'benchmesh-serial-service', 'config.yaml')
  const destConfig = path.join(userDataDir, 'config.yaml')

  copyFileIfNotExists(sourceConfig, destConfig)

  // Create symlink to custom Node-RED nodes
  const customNodesSource = path.join(projectRoot, 'node-red-contrib-benchmesh')
  const customNodesLink = path.join(nodeRedDir, 'node_modules', 'node-red-contrib-benchmesh')

  if (fs.existsSync(customNodesSource)) {
    createSymlinkIfNotExists(customNodesSource, customNodesLink)
  } else {
    console.warn('Warning: Custom Node-RED nodes not found at', customNodesSource)
  }

  console.log('User data initialization complete')
  console.log('=========================================')

  return {
    userDataDir,
    configPath: destConfig,
    nodeRedDir,
    logsDir
  }
}

module.exports = {
  getUserDataDir,
  initializeUserData
}
