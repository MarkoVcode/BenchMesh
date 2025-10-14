# Deployment Guide

This guide covers deploying BenchMesh for production use, including systemd services, Docker containers, reverse proxies, and security considerations.

## Table of Contents

- [Deployment Options](#deployment-options)
- [Systemd Service](#systemd-service)
- [Docker Deployment](#docker-deployment)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [Security Hardening](#security-hardening)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Tuning](#performance-tuning)

## Deployment Options

BenchMesh can be deployed in several ways:

1. **Local Service** - Run directly on the hardware with instruments
2. **Electron Desktop App** - Standalone desktop application for Windows/Mac/Linux
3. **Systemd Service** - Auto-start on boot with systemd
4. **Docker Container** - Containerized deployment
5. **Remote Access** - Expose via reverse proxy with SSL

## Electron Desktop Application

BenchMesh can be packaged as a standalone desktop application using Electron, providing a native app experience for Windows, macOS, and Linux.

###Overview

**Distribution modes**:
- **Self-hosted** (web): Traditional web-based deployment using `./start.sh`
- **Electron app**: Standalone desktop application with embedded services

### Prerequisites

**For development**:
- Node.js 18+ and npm
- Python 3.8+
- All dependencies installed (see Getting Started guide)

**For building**:
```bash
cd electron
npm install
```

### Development Mode

**Option 1: Self-Hosted (Web-based)**
```bash
./start.sh
# Access at http://localhost:57666
```

**Option 2: Electron Development**
```bash
# Terminal 1: Start backend services
./start.sh

# Terminal 2: Start Electron in dev mode
cd electron
NODE_ENV=development npm start
```

### Building Electron App

**Build for current platform**:
```bash
cd electron
npm run build
```

**Build for specific platforms**:
```bash
# Linux (AppImage, .deb)
npm run build:linux

# Windows (installer, portable)
npm run build:win

# macOS (DMG, ZIP)
npm run build:mac
```

Built applications will be in `dist/` directory.

### Distribution Packages

**Linux**:
- **AppImage**: `dist/BenchMesh-1.0.0.AppImage` - Portable, no installation
- **DEB Package**: `dist/BenchMesh_1.0.0_amd64.deb` - For Debian/Ubuntu

**Windows**:
- **Installer**: `dist/BenchMesh Setup 1.0.0.exe` - Standard installer
- **Portable**: `dist/BenchMesh 1.0.0.exe` - Run directly, no installation

**macOS**:
- **DMG**: `dist/BenchMesh-1.0.0.dmg` - Drag-and-drop installation
- **ZIP**: `dist/BenchMesh-1.0.0-mac.zip` - Extract and run

### Architecture

```
┌─────────────────────────────────────┐
│     Electron Main Process           │
│  ┌────────────────────────────────┐ │
│  │  • Manages app lifecycle       │ │
│  │  • Spawns Python backend       │ │
│  │  • Spawns Node-RED service     │ │
│  │  • Creates browser window      │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌─────────────┐         ┌──────────────┐
│   Python    │         │   Node-RED   │
│   Backend   │◄────────┤   Service    │
│  (FastAPI)  │         │  (Port 1880) │
│(Port 57666) │         └──────────────┘
└─────────────┘
       │
       ▼
┌──────────────────────┐
│  Electron Renderer   │
│  (React Frontend)    │
└──────────────────────┘
```

### System Requirements

**Runtime**:
- Operating System: Linux, Windows 10+, or macOS 10.14+
- Python 3.8+
- Serial port access for instrument communication

**Build** (development only):
- All runtime requirements
- Git
- Node.js 18+
- Platform-specific build tools:
  - Linux: `build-essential`
  - Windows: Visual Studio Build Tools
  - macOS: Xcode Command Line Tools

### Configuration

**Backend port**: Default 57666 (configure in `electron/main.js`)

**Node-RED port**: Default 1880 (configure in `electron/main.js`)

**Development mode**: Set `NODE_ENV=development` to:
- Connect to existing dev servers
- Enable DevTools
- Skip service spawning

### Deployment Comparison

| Feature | Self-Hosted | Electron App |
|---------|-------------|--------------|
| Installation | Manual setup | Single installer |
| Updates | Git pull | Auto-update capable |
| Access | Any browser | Dedicated window |
| Multi-user | Yes (networked) | Single user |
| Resources | Lighter | ~200MB app |
| Platform | Any with browser | Windows/Mac/Linux |
| Serial Access | Direct | Direct |

### Distribution Checklist

Before distributing:

- [ ] Frontend built: `cd benchmesh-serial-service/frontend && npm run build`
- [ ] Python dependencies listed in `requirements.txt`
- [ ] Node-RED flows tested
- [ ] All instrument drivers included
- [ ] Documentation updated
- [ ] Version number updated in `package.json`
- [ ] Icons and branding added
- [ ] Tested on target platforms
- [ ] Code signed (production only)

### Code Signing (Production)

**macOS**:
```bash
# Requires Apple Developer certificate
export CSC_LINK="path/to/certificate.p12"
export CSC_KEY_PASSWORD="certificate-password"
npm run build:mac
```

**Windows**:
```bash
# Requires code signing certificate
npm run build:win
```

### Troubleshooting

**Services not starting**:
- Check Python is in PATH
- Verify `requirements.txt` dependencies installed
- Check ports 57666 and 1880 are available

**Blank window**:
- Wait 2-3 seconds for services to start
- Check console for backend errors
- Verify frontend built: `cd benchmesh-serial-service/frontend && npm run build`

**Build fails**:
- Ensure all dependencies installed
- Check Node.js version (18+)
- Verify Python backend can run standalone

## Systemd Service

### Creating the Service

Create a systemd unit file for automatic startup:

```bash
sudo nano /etc/systemd/system/benchmesh.service
```

```ini
[Unit]
Description=BenchMesh Serial Service
After=network.target

[Service]
Type=simple
User=benchmesh
Group=dialout
WorkingDirectory=/opt/benchmesh
Environment="PYTHONPATH=/opt/benchmesh/benchmesh-serial-service/src"
Environment="BENCHMESH_CONFIG=/opt/benchmesh/config.yaml"
ExecStart=/opt/benchmesh/venv/bin/uvicorn benchmesh_service.api:app --host 0.0.0.0 --port 57666
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/benchmesh/logs

[Install]
WantedBy=multi-user.target
```

### Installation Steps

```bash
# Create dedicated user
sudo useradd -r -s /bin/false -G dialout benchmesh

# Create installation directory
sudo mkdir -p /opt/benchmesh
sudo chown benchmesh:dialout /opt/benchmesh

# Clone repository
cd /opt/benchmesh
sudo -u benchmesh git clone https://github.com/MarkoVcode/BenchMesh.git .

# Create virtual environment
sudo -u benchmesh python3 -m venv venv
sudo -u benchmesh venv/bin/pip install -r benchmesh-serial-service/requirements.txt

# Create logs directory
sudo -u benchmesh mkdir -p /opt/benchmesh/logs

# Copy config file
sudo -u benchmesh cp config.yaml.example config.yaml
sudo -u benchmesh nano config.yaml  # Edit configuration

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable benchmesh
sudo systemctl start benchmesh

# Check status
sudo systemctl status benchmesh
```

### Service Management

```bash
# Start service
sudo systemctl start benchmesh

# Stop service
sudo systemctl stop benchmesh

# Restart service
sudo systemctl restart benchmesh

# View logs
sudo journalctl -u benchmesh -f

# View recent errors
sudo journalctl -u benchmesh -p err

# Enable auto-start on boot
sudo systemctl enable benchmesh

# Disable auto-start
sudo systemctl disable benchmesh
```

### Node-RED Service

Create a separate service for Node-RED:

```bash
sudo nano /etc/systemd/system/benchmesh-nodered.service
```

```ini
[Unit]
Description=BenchMesh Node-RED
After=network.target benchmesh.service

[Service]
Type=simple
User=benchmesh
Group=dialout
WorkingDirectory=/opt/benchmesh
Environment="NODE_RED_HOME=/opt/benchmesh/.node-red"
ExecStart=/usr/bin/node-red
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable benchmesh-nodered
sudo systemctl start benchmesh-nodered
```

## Docker Deployment

### Dockerfile

Create `Dockerfile` in repository root:

```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY benchmesh-serial-service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY benchmesh-serial-service/ benchmesh-serial-service/
COPY config.yaml .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 57666

# Set environment
ENV PYTHONPATH=/app/benchmesh-serial-service/src
ENV BENCHMESH_CONFIG=/app/config.yaml

# Run application
CMD ["uvicorn", "benchmesh_service.api:app", "--host", "0.0.0.0", "--port", "57666"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  benchmesh:
    build: .
    container_name: benchmesh
    ports:
      - "57666:57666"
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"  # Map serial devices
      - "/dev/ttyUSB1:/dev/ttyUSB1"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./logs:/app/logs
    restart: unless-stopped
    environment:
      - PYTHONPATH=/app/benchmesh-serial-service/src
      - BENCHMESH_CONFIG=/app/config.yaml

  nodered:
    image: nodered/node-red:latest
    container_name: benchmesh-nodered
    ports:
      - "1880:1880"
    volumes:
      - node-red-data:/data
    depends_on:
      - benchmesh
    restart: unless-stopped

volumes:
  node-red-data:
```

### Building and Running

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f benchmesh

# Stop services
docker-compose down

# Restart service
docker-compose restart benchmesh

# Update and restart
git pull
docker-compose build
docker-compose up -d
```

### Docker with USB Devices

Serial devices require privileged access:

```yaml
services:
  benchmesh:
    privileged: true  # Required for serial devices
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
      - "/dev/ttyUSB1:/dev/ttyUSB1"
```

Or use device group permissions:

```yaml
services:
  benchmesh:
    group_add:
      - dialout
    devices:
      - "/dev/ttyUSB0:/dev/ttyUSB0"
```

## Reverse Proxy Setup

### Nginx

Create `/etc/nginx/sites-available/benchmesh`:

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name benchmesh.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name benchmesh.example.com;

    # SSL certificates (use certbot for Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/benchmesh.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/benchmesh.example.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Proxy to BenchMesh
    location / {
        proxy_pass http://localhost:57666;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Optional: Basic authentication
    # auth_basic "BenchMesh Lab Access";
    # auth_basic_user_file /etc/nginx/.htpasswd;
}

# Node-RED (optional)
server {
    listen 443 ssl http2;
    server_name nodered.example.com;

    ssl_certificate /etc/letsencrypt/live/nodered.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nodered.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:1880;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/benchmesh /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d benchmesh.example.com

# Auto-renewal (certbot sets up cron job automatically)
sudo certbot renew --dry-run
```

### Apache

Create `/etc/apache2/sites-available/benchmesh.conf`:

```apache
<VirtualHost *:80>
    ServerName benchmesh.example.com
    Redirect permanent / https://benchmesh.example.com/
</VirtualHost>

<VirtualHost *:443>
    ServerName benchmesh.example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/benchmesh.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/benchmesh.example.com/privkey.pem

    ProxyPreserveHost On
    ProxyPass / http://localhost:57666/
    ProxyPassReverse / http://localhost:57666/

    # WebSocket support
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteRule /(.*)           ws://localhost:57666/$1 [P,L]
</VirtualHost>
```

Enable required modules and site:

```bash
sudo a2enmod proxy proxy_http proxy_wstunnel ssl rewrite
sudo a2ensite benchmesh
sudo systemctl reload apache2
```

## Security Hardening

### Network Security

1. **Firewall Configuration**:

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (if using reverse proxy)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Block direct access to BenchMesh (use reverse proxy only)
sudo ufw deny 57666/tcp

# Enable firewall
sudo ufw enable
```

2. **SSH Tunnel** for remote access (no reverse proxy):

```bash
# From remote machine
ssh -L 57666:localhost:57666 user@lab-server

# Access via http://localhost:57666
```

### Application Security

1. **Create dedicated user** (see Systemd Service section)

2. **File permissions**:

```bash
# Set ownership
sudo chown -R benchmesh:dialout /opt/benchmesh

# Restrict config file
sudo chmod 600 /opt/benchmesh/config.yaml

# Restrict logs directory
sudo chmod 750 /opt/benchmesh/logs
```

3. **Environment isolation**:

```bash
# Use virtual environment
python3 -m venv venv
source venv/bin/activate
```

4. **Update dependencies regularly**:

```bash
pip list --outdated
pip install --upgrade -r requirements.txt
```

### Authentication

BenchMesh has no built-in authentication. Add authentication via:

1. **Nginx Basic Auth**:

```bash
# Create password file
sudo apt-get install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin

# Add to nginx config
auth_basic "BenchMesh";
auth_basic_user_file /etc/nginx/.htpasswd;
```

2. **OAuth2 Proxy**:

```bash
# Install oauth2-proxy
wget https://github.com/oauth2-proxy/oauth2-proxy/releases/download/v7.4.0/oauth2-proxy-v7.4.0.linux-amd64.tar.gz
tar xzf oauth2-proxy-v7.4.0.linux-amd64.tar.gz

# Configure oauth2-proxy for Google/GitHub/etc.
./oauth2-proxy --upstream=http://localhost:57666 --http-address=0.0.0.0:4180
```

## Monitoring

### Log Monitoring

1. **Centralized logging with Loki** (optional):

```yaml
# docker-compose.yml
services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - ./logs:/var/log/benchmesh:ro
      - ./promtail-config.yaml:/etc/promtail/config.yaml
    command: -config.file=/etc/promtail/config.yaml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
```

2. **System monitoring with htop/glances**:

```bash
sudo apt-get install htop glances
htop
```

### Health Checks

Create health check endpoint in `api.py`:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "devices": len(manager.connections)
    }
```

Monitor with:

```bash
# Simple HTTP check
curl http://localhost:57666/health

# Continuous monitoring
watch -n 10 curl -s http://localhost:57666/health
```

### Uptime Monitoring

Use external service like:
- [Uptime Robot](https://uptimerobot.com/)
- [Pingdom](https://www.pingdom.com/)
- [StatusCake](https://www.statuscake.com/)

Or self-hosted:
- [Uptime Kuma](https://github.com/louislam/uptime-kuma)

## Backup and Recovery

### Configuration Backup

```bash
# Create backup script
cat > /opt/benchmesh/backup.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/benchmesh/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup config
cp /opt/benchmesh/config.yaml "$BACKUP_DIR/config_$TIMESTAMP.yaml"

# Backup Node-RED flows
cp -r /opt/benchmesh/.node-red "$BACKUP_DIR/node-red_$TIMESTAMP"

# Remove old backups (keep last 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
EOF

chmod +x /opt/benchmesh/backup.sh

# Schedule daily backup
sudo crontab -e
# Add: 0 2 * * * /opt/benchmesh/backup.sh
```

### Recovery

```bash
# Restore config
cp /opt/benchmesh/backups/config_YYYYMMDD_HHMMSS.yaml /opt/benchmesh/config.yaml

# Restore Node-RED flows
rm -rf /opt/benchmesh/.node-red
cp -r /opt/benchmesh/backups/node-red_YYYYMMDD_HHMMSS /opt/benchmesh/.node-red

# Restart services
sudo systemctl restart benchmesh
sudo systemctl restart benchmesh-nodered
```

## Performance Tuning

### Polling Optimization

Adjust polling intervals in driver manifests:

```json
{
  "polling": {
    "methods": ["poll_status"],
    "interval": 5.0  // Increase interval to reduce CPU load
  }
}
```

### Python Optimization

1. **Use PyPy** for improved performance (optional):

```bash
sudo apt-get install pypy3
pypy3 -m venv venv
venv/bin/pip install -r requirements.txt
```

2. **Increase worker processes** (if using gunicorn):

```bash
gunicorn benchmesh_service.api:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:57666
```

### System Tuning

1. **Increase open file limits**:

```bash
# Edit /etc/security/limits.conf
benchmesh soft nofile 4096
benchmesh hard nofile 8192
```

2. **Disable USB autosuspend**:

```bash
# Edit /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash usbcore.autosuspend=-1"

# Update grub
sudo update-grub
```

## Production Checklist

Before deploying to production:

- [ ] Create dedicated user account
- [ ] Set up systemd service with auto-restart
- [ ] Configure firewall (ufw/iptables)
- [ ] Set up SSL with Let's Encrypt
- [ ] Configure reverse proxy (nginx/apache)
- [ ] Enable authentication (basic auth or OAuth)
- [ ] Set up log rotation
- [ ] Configure automated backups
- [ ] Set up monitoring and health checks
- [ ] Test recovery procedures
- [ ] Document deployment steps
- [ ] Create runbook for common issues

## Related Documentation

- [Getting Started](Getting-Started) - Initial setup
- [Configuration](Configuration) - Config file format
- [Troubleshooting](Troubleshooting) - Common issues
- [Security Hardening](https://benchmesh.example.com/security) - Advanced security
