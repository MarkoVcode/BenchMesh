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
const crypto = require('crypto')

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
 * Generate a cryptographically secure random secret
 * @param {number} length - Length of the secret in bytes (default: 32)
 * @returns {string} Hex-encoded random secret
 */
function generateSecureSecret(length = 32) {
  return crypto.randomBytes(length).toString('hex')
}

/**
 * Get or create Node-RED credential secret
 * Generates a secure random secret and stores it persistently in user data directory.
 * This secret is used by Node-RED to encrypt flow credentials.
 *
 * @param {string} nodeRedDir - Path to Node-RED user directory
 * @returns {string} The credential secret
 */
function getOrCreateCredentialSecret(nodeRedDir) {
  const secretFile = path.join(nodeRedDir, '.credentials-secret')

  // Read existing secret if available
  if (fs.existsSync(secretFile)) {
    try {
      const secret = fs.readFileSync(secretFile, 'utf8').trim()
      if (secret.length > 0) {
        console.log('Using existing Node-RED credential secret')
        return secret
      }
    } catch (error) {
      console.warn('Failed to read credential secret, generating new one:', error.message)
    }
  }

  // Generate new secret
  const secret = generateSecureSecret(32) // 256-bit security
  try {
    fs.writeFileSync(secretFile, secret, { mode: 0o600 }) // Owner read/write only
    console.log('Generated new Node-RED credential secret')
    console.log('⚠️  IMPORTANT: Backup ~/.benchmesh/node-red/.credentials-secret for data recovery')
    return secret
  } catch (error) {
    console.error('Failed to save credential secret:', error.message)
    throw new Error('Could not persist Node-RED credential secret')
  }
}

/**
 * Update Node-RED settings.js with credential secret and iframe embedding support
 * @param {string} nodeRedDir - Path to Node-RED user directory
 * @param {string} credentialSecret - The credential secret to configure
 */
function updateNodeRedSettings(nodeRedDir, credentialSecret) {
  const settingsPath = path.join(nodeRedDir, 'settings.js')

  if (!fs.existsSync(settingsPath)) {
    console.warn('Node-RED settings.js not found, will be created on first run')
    return
  }

  try {
    let settings = fs.readFileSync(settingsPath, 'utf8')
    let modified = false

    // Configure credentialSecret
    const activeSecretRegex = /^\s*credentialSecret:\s*["'].*["']/m
    if (!activeSecretRegex.test(settings)) {
      const commentedSecretRegex = /(\s*)\/\/credentialSecret:\s*["'].*["']/
      if (commentedSecretRegex.test(settings)) {
        settings = settings.replace(
          commentedSecretRegex,
          `$1credentialSecret: "${credentialSecret}"`
        )
        console.log('✓ Configured Node-RED credentialSecret')
        modified = true
      } else {
        console.warn('Could not find credentialSecret line in settings.js')
      }
    }

    // Configure httpAdminMiddleware for iframe embedding
    const activeMiddlewareRegex = /^\s*httpAdminMiddleware:\s*function/m
    if (!activeMiddlewareRegex.test(settings)) {
      // Replace commented httpAdminMiddleware with active configuration
      const commentedMiddlewareRegex = /(\s*)\/\/ httpAdminMiddleware: function\(req,res,next\) \{[\s\S]*?\/\/\s*next\(\);\s*\/\/ \}/
      if (commentedMiddlewareRegex.test(settings)) {
        const middlewareConfig = `$1httpAdminMiddleware: function(req,res,next) {
$1    // Allow embedding in iframe from same origin (for BenchMesh workbench integration)
$1    res.removeHeader('X-Frame-Options');
$1    res.setHeader('Content-Security-Policy', "frame-ancestors 'self'");
$1    next();
$1}`
        settings = settings.replace(commentedMiddlewareRegex, middlewareConfig)
        console.log('✓ Configured Node-RED iframe embedding support')
        modified = true
      }
    }

    // Write changes if any modifications were made
    if (modified) {
      fs.writeFileSync(settingsPath, settings, 'utf8')
      console.log('✓ Node-RED settings.js updated successfully')
    } else {
      console.log('Node-RED settings.js already configured')
    }
  } catch (error) {
    console.error('Failed to update Node-RED settings:', error.message)
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

  // Setup Node-RED credential encryption
  console.log('Configuring Node-RED credential encryption...')
  const credentialSecret = getOrCreateCredentialSecret(nodeRedDir)
  updateNodeRedSettings(nodeRedDir, credentialSecret)

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
