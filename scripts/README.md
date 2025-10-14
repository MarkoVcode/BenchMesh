# BenchMesh Scripts

This directory contains utility scripts for development, testing, and deployment.

## Development & Testing Scripts

### test-automation-ui.sh
Tests the automation UI integration with Node-RED.

**Usage**:
```bash
./scripts/test-automation-ui.sh
```

**Purpose**:
- Checks old inject nodes in Node-RED
- Verifies BenchMesh automations API
- Calculates expected UI state
- Displays button color and counter badge expectations

**When to use**: After making changes to automation UI or Node-RED integration.

### verify-automation.sh
Verifies the automation integration is working correctly.

**Usage**:
```bash
./scripts/verify-automation.sh
```

**Purpose**:
- Tests `/benchmesh/automations` API endpoint
- Shows expected UI state (button color and badge)
- Provides detailed info about running automations
- Gives next steps for verification

**When to use**: After importing automation flows or troubleshooting automation issues.

### restart-and-test.sh
Provides instructions for restarting services and testing automation.

**Usage**:
```bash
./scripts/restart-and-test.sh
```

**Purpose**:
- Displays step-by-step instructions for service restart
- Guides through verification process
- Shows expected results

**When to use**: After code changes that require service restart.

## Documentation Scripts

### sync-wiki.sh
Syncs documentation from `docs/` directory to GitHub wiki.

**Usage**:
```bash
./scripts/sync-wiki.sh                                    # Auto-detect wiki URL
./scripts/sync-wiki.sh git@github.com:user/repo.wiki.git # Specify wiki URL
```

**Purpose**:
- Clones the GitHub wiki repository
- Copies all markdown files from `docs/`
- Copies static assets (images)
- Commits and pushes changes to wiki

**When to use**: After updating documentation files in `docs/` directory.

**Files synced**:
- Home.md
- Getting-Started.md
- Configuration.md
- Automation.md
- API-Reference.md
- Architecture.md
- Deployment.md
- Driver-Development.md
- Testing.md
- Troubleshooting.md
- static/* (all images)

### update-docs.sh
Updates documentation (if applicable).

**Usage**:
```bash
./scripts/update-docs.sh
```

## Build & Release Scripts

### prepare-release.sh
Prepares a new release version.

**Usage**:
```bash
./scripts/prepare-release.sh
```

**Purpose**:
- Updates version numbers
- Prepares changelog
- Creates release artifacts

**When to use**: Before creating a new release tag.

## Script Conventions

All scripts in this directory follow these conventions:

1. **Naming**: Use kebab-case (e.g., `test-automation-ui.sh`)
2. **Executable**: All scripts have executable permissions (`chmod +x`)
3. **Shebang**: All scripts start with `#!/bin/bash`
4. **Error handling**: Use `set -e` for critical scripts
5. **Documentation**: Include purpose and usage in this README

## Adding New Scripts

When adding a new script:

1. Place it in the `scripts/` directory
2. Use kebab-case naming
3. Make it executable: `chmod +x scripts/your-script.sh`
4. Add documentation to this README
5. Update any relevant documentation that references the script

## Troubleshooting

### Permission Denied
If you get a permission denied error:
```bash
chmod +x scripts/script-name.sh
```

### Script Not Found
Always run scripts from the repository root:
```bash
# Correct
./scripts/script-name.sh

# Incorrect (from scripts/ directory)
./script-name.sh
```

### Path Issues
Scripts assume they're run from the repository root. If a script fails with path errors, check your current directory:
```bash
pwd  # Should show: /path/to/BenchMesh
```
