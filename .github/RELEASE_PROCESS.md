# Release Process

This document describes how to create a new release of BenchMesh.

## Automated Release Process

BenchMesh uses GitHub Actions to automatically build and publish releases when you push a version tag.

### Quick Release Steps

1. **Update version numbers:**
   ```bash
   # Update package.json
   npm version patch  # or minor, or major

   # Update electron/package.json
   cd electron
   npm version patch
   cd ..

   # Update version in benchmesh-serial-service/frontend/package.json
   cd benchmesh-serial-service/frontend
   npm version patch
   cd ../..
   ```

2. **Update CHANGELOG.md:**
   ```bash
   # Add release notes
   vim CHANGELOG.md
   ```

3. **Commit and tag:**
   ```bash
   git add .
   git commit -m "Release v1.0.0"
   git tag v1.0.0
   git push origin main
   git push origin v1.0.0
   ```

4. **Wait for builds:**
   - GitHub Actions will automatically build for Linux, Windows, and macOS
   - Check progress at: https://github.com/YOUR_ORG/BenchMesh/actions
   - Release will be created with all artifacts

### What Gets Built

When you push a tag like `v1.0.0`, the workflow automatically builds:

#### Electron Desktop Apps
- **Linux**:
  - `BenchMesh-1.0.0-Linux-x86_64.AppImage` (portable)
  - `BenchMesh-1.0.0-amd64.deb` (Debian/Ubuntu installer)

- **Windows**:
  - `BenchMesh-Setup-1.0.0.exe` (installer)
  - `BenchMesh-Portable-1.0.0.exe` (portable)

- **macOS**:
  - `BenchMesh-1.0.0-macOS.dmg` (disk image)
  - `BenchMesh-1.0.0-macOS.zip` (archive)

#### Self-Hosted Web App
- `benchmesh-web-1.0.0.tar.gz` (complete package with install script)
- `checksums-web.txt` (SHA256 checksums)

## Manual Release Process

If you need to build manually:

### 1. Prepare Release

```bash
# Ensure everything is committed
git status

# Update version
npm version <major|minor|patch>

# Update CHANGELOG.md with release notes
```

### 2. Build Frontend

```bash
cd benchmesh-serial-service/frontend
npm ci
npm run build
cd ../..
```

### 3. Build Electron Apps

```bash
# Linux
npm run electron:build:linux

# Windows (requires Windows or Wine)
npm run electron:build:win

# macOS (requires macOS)
npm run electron:build:mac
```

### 4. Create Self-Hosted Package

```bash
# Create archive
tar -czf benchmesh-web-1.0.0.tar.gz \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=dist \
  --exclude=electron/node_modules \
  benchmesh-serial-service \
  .node-red \
  start.sh \
  package.json \
  package-lock.json \
  README.md \
  STARTUP.md

# Generate checksum
sha256sum benchmesh-web-1.0.0.tar.gz > checksums.txt
```

### 5. Create GitHub Release

```bash
# Create tag
git tag v1.0.0
git push origin v1.0.0

# Or use GitHub CLI
gh release create v1.0.0 \
  --title "BenchMesh v1.0.0" \
  --notes-file CHANGELOG.md \
  dist/BenchMesh-*.AppImage \
  dist/BenchMesh-*.deb \
  dist/BenchMesh-Setup-*.exe \
  dist/BenchMesh-Portable-*.exe \
  dist/BenchMesh-*.dmg \
  dist/BenchMesh-*-mac.zip \
  benchmesh-web-*.tar.gz \
  checksums.txt
```

## Version Numbering

BenchMesh uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality, backwards compatible
- **PATCH** version: Bug fixes, backwards compatible

### Pre-release Versions

- `v1.0.0-alpha.1` - Alpha release
- `v1.0.0-beta.1` - Beta release
- `v1.0.0-rc.1` - Release candidate

Pre-release tags automatically mark the GitHub release as "pre-release".

## Release Checklist

Before creating a release:

- [ ] All tests pass: `npm test` (if configured)
- [ ] Frontend builds: `cd benchmesh-serial-service/frontend && npm run build`
- [ ] Backend runs: `cd benchmesh-serial-service && python -m pytest` (if tests exist)
- [ ] Electron builds locally: `npm run electron:build`
- [ ] Version numbers updated in all package.json files
- [ ] CHANGELOG.md updated with release notes
- [ ] README.md updated if needed
- [ ] Documentation reviewed
- [ ] All features tested manually
- [ ] Known issues documented

## Continuous Integration

### Test Workflow (`.github/workflows/test.yml`)

Runs on every push and pull request:
- Tests frontend build
- Tests backend loads
- Tests Electron build process

### Release Workflow (`.github/workflows/release-electron.yml`)

Runs when you push a version tag (e.g., `v1.0.0`):
1. Creates GitHub release
2. Builds Electron apps for all platforms in parallel
3. Builds self-hosted archive
4. Uploads all artifacts to the release

## Troubleshooting

### Build Fails on GitHub Actions

**Frontend build fails:**
```bash
# Test locally first
cd benchmesh-serial-service/frontend
npm ci
npm run build
```

**Electron build fails:**
```bash
# Check electron build locally
npm run electron:build
```

**macOS build fails:**
- macOS builds require macOS runner
- Check Xcode version compatibility
- Verify code signing (if enabled)

### Release Asset Upload Fails

If asset upload fails:
1. Go to the GitHub release page
2. Manually upload the built files from `dist/` directory
3. Or re-run the failed workflow job

### Version Mismatch

If versions don't match:
```bash
# Sync all package.json versions
./scripts/sync-versions.sh 1.0.0  # if you create this script
```

## Post-Release

After release is published:

1. **Announce release:**
   - Update project website/documentation
   - Post on social media/forums
   - Notify users

2. **Monitor issues:**
   - Watch for bug reports
   - Check download statistics
   - Review user feedback

3. **Plan next release:**
   - Create milestone for next version
   - Prioritize features/fixes
   - Update roadmap

## Security

### Code Signing (Optional)

For production releases, consider code signing:

**macOS:**
```bash
export CSC_LINK="path/to/certificate.p12"
export CSC_KEY_PASSWORD="password"
npm run electron:build:mac
```

**Windows:**
- Requires Windows code signing certificate
- Configure in `electron/package.json` build section

Add these as GitHub Secrets:
- `CSC_LINK` - Certificate file (base64 encoded)
- `CSC_KEY_PASSWORD` - Certificate password
- `WIN_CSC_LINK` - Windows certificate
- `WIN_CSC_KEY_PASSWORD` - Windows certificate password

Update workflow to use secrets:
```yaml
env:
  CSC_LINK: ${{ secrets.CSC_LINK }}
  CSC_KEY_PASSWORD: ${{ secrets.CSC_KEY_PASSWORD }}
```

## Rollback

If a release has critical issues:

1. **Delete the release:**
   ```bash
   gh release delete v1.0.0
   git tag -d v1.0.0
   git push origin :refs/tags/v1.0.0
   ```

2. **Fix issues and re-release:**
   ```bash
   # Fix code
   git commit -am "Fix critical issue"

   # Re-tag with patch version
   git tag v1.0.1
   git push origin v1.0.1
   ```

## Support

For questions about the release process:
- Check GitHub Actions logs
- Review this documentation
- Open an issue for process improvements
