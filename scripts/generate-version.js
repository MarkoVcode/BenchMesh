#!/usr/bin/env node
/**
 * Generate version.json from package.json
 *
 * This script ensures version information is consistent across the application
 * by reading from package.json (single source of truth) and generating version.json
 *
 * Usage: node scripts/generate-version.js
 */

const fs = require('fs')
const path = require('path')

// Paths
const rootDir = path.join(__dirname, '..')
const packageJsonPath = path.join(rootDir, 'package.json')
const versionJsonPath = path.join(rootDir, 'version.json')

try {
  // Read package.json
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'))

  // Extract version information
  const versionInfo = {
    name: packageJson.name.charAt(0).toUpperCase() + packageJson.name.slice(1), // Capitalize
    version: packageJson.version,
    description: packageJson.description || 'Lab Instrument Control System'
  }

  // Write version.json
  fs.writeFileSync(
    versionJsonPath,
    JSON.stringify(versionInfo, null, 2) + '\n',
    'utf8'
  )

  console.log('✓ Generated version.json')
  console.log(`  Name: ${versionInfo.name}`)
  console.log(`  Version: ${versionInfo.version}`)
  console.log(`  Description: ${versionInfo.description}`)

} catch (error) {
  console.error('✗ Failed to generate version.json:', error.message)
  process.exit(1)
}
