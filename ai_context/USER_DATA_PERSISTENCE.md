# User Data Persistence

BenchMesh stores all user data in `~/.benchmesh/` to ensure configurations, Node-RED flows, and recordings persist across app updates and installations.

## Directory Structure

```
~/.benchmesh/
├── config.yaml          # Device configurations (copied from default on first run)
├── node-red/            # Node-RED flows and data
│   ├── flows.json
│   ├── settings.js
│   ├── .credentials-secret  # Encryption key for Node-RED credentials (⚠️ BACKUP THIS FILE)
│   ├── node_modules/
│   │   └── node-red-contrib-benchmesh -> symlink to project custom nodes
│   └── ...
├── recordings.db        # SQLite database for recording feature
└── logs/                # Application logs (Electron and web modes)
    ├── benchmesh_service.log      # Serial service application logs (rotating, max 50MB)
    ├── uvicorn.log                # FastAPI/uvicorn stdout (Electron mode)
    ├── uvicorn_error.log          # FastAPI/uvicorn stderr (Electron mode)
    ├── node-red.log               # Node-RED stdout (Electron mode)
    └── node-red_error.log         # Node-RED stderr (Electron mode)
```

## Initialization

### Electron Mode
- On app startup, `electron/init-user-data.js` creates `~/.benchmesh/` structure
- Copies default `config.yaml` if not present
- Creates symlink to custom Node-RED nodes (`node-red-contrib-benchmesh`)
- Generates Node-RED credential encryption secret (`.credentials-secret`)
- Sets environment variables automatically

### Web/Browser Mode
- `start.sh` creates `~/.benchmesh/` structure
- Copies default `config.yaml` if not present
- Creates symlink to custom Node-RED nodes (`node-red-contrib-benchmesh`)
- Node-RED generates credential secret on first run
- Exports environment variables for backend services

## Configuration

Both modes use these environment variables:
- `BENCHMESH_CONFIG`: Path to config.yaml (set to `~/.benchmesh/config.yaml`)
- `BENCHMESH_DATA_DIR`: User data directory (set to `~/.benchmesh/`)

### Configuration Persistence
- Changes made through the Configuration modal (UI) are automatically persisted to `~/.benchmesh/config.yaml`
- The `POST /config` API endpoint saves changes atomically using a temp file + rename strategy
- Configuration survives app restarts and updates
- To manually edit config: modify `~/.benchmesh/config.yaml` and restart the app

## Node-RED Credential Secret

**⚠️ CRITICAL: This file must be backed up to ensure credential recovery**

BenchMesh automatically manages a persistent encryption key for Node-RED credentials stored at:
```
~/.benchmesh/node-red/.credentials-secret
```

### How it works
- **First run**: Generates a cryptographically secure 256-bit (32-byte) random secret
- **Subsequent runs**: Reads existing secret from `.credentials-secret` file
- **Automatic configuration**: Updates Node-RED `settings.js` with the credential secret
- **File permissions**: Restricted to owner-only (0600) for security
- **Persistence**: Survives app updates and reinstalls

### Why this matters
- Node-RED encrypts stored credentials (API keys, passwords, tokens) using this secret
- Without this file, encrypted credentials become **permanently unrecoverable**
- Each BenchMesh installation should have its own unique secret

### Backup recommendations

```bash
# Backup the credential secret (REQUIRED for credential recovery)
cp ~/.benchmesh/node-red/.credentials-secret ~/.benchmesh.backup/

# Or include it in your full user data backup
cp -r ~/.benchmesh ~/.benchmesh.backup
```

### Recovery scenarios
- **Lost secret file**: All Node-RED credentials must be re-entered manually
- **Restored from backup**: Credentials automatically decrypt if secret is restored
- **Fresh install**: New secret is generated, old credentials won't decrypt

## Backup and Migration

### To backup your configuration

```bash
# Backup entire user data directory (RECOMMENDED - includes credential secret)
cp -r ~/.benchmesh ~/.benchmesh.backup

# Or backup individual critical files
cp ~/.benchmesh/config.yaml ~/.benchmesh/config.yaml.backup
cp ~/.benchmesh/node-red/.credentials-secret ~/.benchmesh/credentials-secret.backup
```

**⚠️ IMPORTANT**: Always include `~/.benchmesh/node-red/.credentials-secret` in backups. Without this file, Node-RED encrypted credentials cannot be recovered.

### To migrate to a new machine

```bash
# Copy user data directory to new machine
scp -r ~/.benchmesh user@newmachine:~/
```

### To reset to defaults

```bash
# Remove user data directory (will recreate on next startup)
rm -rf ~/.benchmesh
```

## Location by Operating System

The user data directory is always `~/.benchmesh/` on all platforms:
- **Linux**: `/home/username/.benchmesh/`
- **macOS**: `/Users/username/.benchmesh/`
- **Windows**: `C:\Users\username\.benchmesh\`

## Application Logging

### Log Location
All application logs are stored in `~/.benchmesh/logs/` directory.

### Log Files
- `benchmesh_service.log` - Serial service application logs (rotating, max 50MB total)
  - Device connections, polling, errors, serial communication
  - Automatically rotates: 10MB per file, keeps 5 backup files
- `uvicorn.log` - FastAPI/uvicorn standard output (Electron mode only)
  - HTTP requests, startup messages, general server output
- `uvicorn_error.log` - FastAPI/uvicorn error output (Electron mode only)
  - Python exceptions, HTTP errors, startup failures
- `node-red.log` - Node-RED standard output (Electron mode only)
  - Flow execution, node messages, startup output
- `node-red_error.log` - Node-RED error output (Electron mode only)
  - Flow errors, node failures, runtime exceptions

### Log Format
All logs include timestamps in ISO 8601 format for correlation across services.

### Viewing Logs

```bash
# View serial service logs (all modes)
tail -f ~/.benchmesh/logs/benchmesh_service.log

# View all logs (Electron mode)
tail -f ~/.benchmesh/logs/*.log

# Search for errors
grep -i error ~/.benchmesh/logs/*.log

# View logs from last hour
find ~/.benchmesh/logs -name "*.log" -exec grep "$(date -d '1 hour ago' -Iseconds)" {} +
```

### Development Mode
- Serial service logs: Repository `logs/benchmesh_service.log`
- Uvicorn/Node-RED: Console output only (not written to files)

## Troubleshooting

### Config not loading
1. Check that `~/.benchmesh/config.yaml` exists
2. Verify file permissions: `chmod 644 ~/.benchmesh/config.yaml`
3. Check logs for parsing errors

### Node-RED flows missing after update
1. Verify `~/.benchmesh/node-red/flows.json` exists
2. Check Node-RED is using correct userDir (shown in startup logs)

### Node-RED custom nodes not showing
1. Check symlink exists: `ls -la ~/.benchmesh/node-red/node_modules/node-red-contrib-benchmesh`
2. Restart Node-RED to reload nodes
3. The symlink is automatically created on startup to link to project's `node-red-contrib-benchmesh/` directory

### Recordings database not found
1. Check `~/.benchmesh/recordings.db` exists
2. Verify `BENCHMESH_DATA_DIR` environment variable is set

### Node-RED credential warning
1. Check if `~/.benchmesh/node-red/.credentials-secret` exists
2. Verify file has correct permissions: `chmod 600 ~/.benchmesh/node-red/.credentials-secret`
3. Check Node-RED settings.js has `credentialSecret` configured (not commented out)
4. If file is missing, a new one will be generated on next startup (old credentials lost)

### Node-RED credentials not working after restore
1. Verify `.credentials-secret` file was included in backup/restore
2. Check that secret file has same content as original installation
3. Ensure file permissions are correct (0600)
4. If secret doesn't match, credentials must be re-entered manually
