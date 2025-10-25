/**
 * Version Management for BenchMesh Electron App
 *
 * Tracks app version changes to detect downgrades that might
 * cause data corruption or incompatibility issues.
 */

const fs = require('fs')
const path = require('path')

/**
 * Compare two semantic version strings
 * @param {string} version1 - First version (e.g., "1.2.3")
 * @param {string} version2 - Second version (e.g., "1.2.4")
 * @returns {number} -1 if version1 < version2, 0 if equal, 1 if version1 > version2
 */
function compareVersions(version1, version2) {
  const v1Parts = version1.split('.').map(Number)
  const v2Parts = version2.split('.').map(Number)

  for (let i = 0; i < Math.max(v1Parts.length, v2Parts.length); i++) {
    const v1Part = v1Parts[i] || 0
    const v2Part = v2Parts[i] || 0

    if (v1Part > v2Part) return 1
    if (v1Part < v2Part) return -1
  }

  return 0
}

/**
 * Load version information from a JSON file
 * @param {string} versionPath - Path to version.json
 * @returns {Object|null} Version object or null if file doesn't exist or is invalid
 */
function loadVersion(versionPath) {
  try {
    if (!fs.existsSync(versionPath)) {
      return null
    }

    const content = fs.readFileSync(versionPath, 'utf8')
    return JSON.parse(content)
  } catch (error) {
    console.error(`Failed to load version from ${versionPath}:`, error.message)
    return null
  }
}

/**
 * Save version information to user data directory
 * @param {string} userDataDir - Path to ~/.benchmesh/
 * @param {Object} versionInfo - Version object to save
 */
function saveVersionToUserData(userDataDir, versionInfo) {
  const versionPath = path.join(userDataDir, 'version.json')

  try {
    fs.writeFileSync(
      versionPath,
      JSON.stringify(versionInfo, null, 2) + '\n',
      'utf8'
    )
    console.log(`Saved version tracking: ${versionPath}`)
  } catch (error) {
    console.error(`Failed to save version to ${versionPath}:`, error.message)
  }
}

/**
 * Check for version downgrade
 * @param {string} projectRoot - Project root directory
 * @param {string} userDataDir - User data directory (~/.benchmesh/)
 * @returns {Object} Object with:
 *   - currentVersion: Current app version object
 *   - lastVersion: Last used app version object (or null)
 *   - isDowngrade: Boolean indicating if current < last
 */
function checkVersionDowngrade(projectRoot, userDataDir) {
  // Load current app version
  const currentVersionPath = path.join(projectRoot, 'version.json')
  const currentVersion = loadVersion(currentVersionPath)

  if (!currentVersion) {
    console.warn('Warning: Could not load current app version from version.json')
    return {
      currentVersion: null,
      lastVersion: null,
      isDowngrade: false
    }
  }

  // Load last used version
  const lastVersionPath = path.join(userDataDir, 'version.json')
  const lastVersion = loadVersion(lastVersionPath)

  // If no previous version exists, this is first run
  if (!lastVersion) {
    console.log('First run detected - no previous version found')
    return {
      currentVersion,
      lastVersion: null,
      isDowngrade: false
    }
  }

  // Compare versions
  const comparison = compareVersions(currentVersion.version, lastVersion.version)
  const isDowngrade = comparison < 0

  if (isDowngrade) {
    console.warn('Version downgrade detected!')
    console.warn(`  Current version: ${currentVersion.version}`)
    console.warn(`  Last used version: ${lastVersion.version}`)
  } else {
    console.log(`Version check passed (current: ${currentVersion.version}, last: ${lastVersion.version})`)
  }

  return {
    currentVersion,
    lastVersion,
    isDowngrade
  }
}

module.exports = {
  compareVersions,
  loadVersion,
  saveVersionToUserData,
  checkVersionDowngrade
}
