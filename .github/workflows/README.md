# GitHub Actions Workflows

This directory contains automated workflows for BenchMesh.

## Workflows

### 1. `test.yml` - Continuous Integration
**Trigger:** Push to main/develop, Pull Requests

**Purpose:** Validates code quality and builds

**Jobs:**
- `test-frontend` - Builds and tests React frontend
- `test-backend` - Tests Python backend
- `test-electron-build` - Validates Electron can build

**Usage:** Runs automatically on every push/PR

---

### 2. `release-electron.yml` - Production Release
**Trigger:** Git tags matching `v*.*.*` (e.g., `v1.0.0`)

**Purpose:** Creates official releases with all platform builds

**Jobs:**
- `create-release` - Creates GitHub release
- `build-linux` - Builds AppImage and DEB for Linux
- `build-windows` - Builds installer and portable for Windows
- `build-macos` - Builds DMG and ZIP for macOS
- `build-self-hosted` - Creates web application archive

**Artifacts:**
- `BenchMesh-{version}-Linux-x86_64.AppImage`
- `BenchMesh-{version}-amd64.deb`
- `BenchMesh-Setup-{version}.exe`
- `BenchMesh-Portable-{version}.exe`
- `BenchMesh-{version}-macOS.dmg`
- `BenchMesh-{version}-macOS.zip`
- `benchmesh-web-{version}.tar.gz`
- `checksums-web.txt`

**How to trigger:**
```bash
git tag v1.0.0
git push origin v1.0.0
```

---

### 3. `draft-release.yml` - Test Release
**Trigger:** Manual (workflow_dispatch)

**Purpose:** Create draft release for testing before official release

**Jobs:**
- Builds subset of platforms (Linux + Web)
- Creates draft release (not visible to public)
- Allows testing build process

**How to trigger:**
1. Go to: Actions → Draft Release → Run workflow
2. Enter version number (e.g., `1.0.0`)
3. Click "Run workflow"
4. Download and test artifacts from draft release
5. Delete draft when done, or publish if ready

---

## Release Process

### Option 1: Automated Release (Recommended)

1. **Prepare release:**
   ```bash
   ./scripts/prepare-release.sh 1.0.0
   ```

2. **Edit CHANGELOG.md** with release notes

3. **Commit and tag:**
   ```bash
   git add .
   git commit -m "Release v1.0.0"
   git tag v1.0.0
   git push origin main --tags
   ```

4. **Wait for builds** - Check GitHub Actions tab

5. **Release published automatically** with all artifacts

### Option 2: Draft Release First (Testing)

1. **Test build first:**
   - Go to Actions → Draft Release
   - Run workflow with version
   - Test downloaded artifacts

2. **If successful, create real release:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

### Option 3: Manual Release

See [RELEASE_PROCESS.md](./RELEASE_PROCESS.md) for manual steps.

---

## Workflow Configuration

### Secrets Required

None currently. For future enhancements:

- `CSC_LINK` - macOS code signing certificate (optional)
- `CSC_KEY_PASSWORD` - Certificate password (optional)
- `WIN_CSC_LINK` - Windows code signing certificate (optional)
- `WIN_CSC_KEY_PASSWORD` - Windows certificate password (optional)

To add secrets:
1. Go to: Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add secret name and value

### Modifying Workflows

**To change build platforms:**
Edit `release-electron.yml` and modify the `build-{platform}` jobs.

**To change artifacts:**
Edit the `Upload` steps in each build job.

**To add code signing:**
Uncomment and configure CSC variables in workflow files.

**To change Node.js version:**
Update `node-version` in `setup-node` steps.

**To change Python version:**
Update `python-version` in `setup-python` steps.

---

## Troubleshooting

### Build Fails

**Check logs:**
1. Go to Actions tab
2. Click on failed workflow run
3. Click on failed job
4. Expand failed step

**Common issues:**

1. **Frontend build fails:**
   - Check `package.json` syntax
   - Verify all dependencies in `package-lock.json`
   - Test locally: `npm run build`

2. **Electron build fails:**
   - Check electron version compatibility
   - Verify system dependencies installed
   - Test locally: `npm run electron:build`

3. **Asset upload fails:**
   - Check file paths in workflow
   - Verify file was created in `dist/`
   - Check upload_url is valid

4. **macOS build fails:**
   - Requires macOS runner (expensive)
   - May need Xcode version update
   - Check code signing setup

### Re-running Failed Builds

1. Go to failed workflow run
2. Click "Re-run failed jobs" or "Re-run all jobs"

### Manual Upload

If automatic upload fails:
1. Build locally: `npm run electron:build`
2. Go to GitHub Releases
3. Edit the release
4. Manually upload files from `dist/`

---

## Performance

### Build Times (Approximate)

- Frontend build: ~2-3 minutes
- Linux Electron: ~5-7 minutes
- Windows Electron: ~5-7 minutes
- macOS Electron: ~7-10 minutes
- Self-hosted archive: ~2 minutes

**Total parallel time:** ~10-12 minutes (all platforms)
**Total sequential time:** ~25-30 minutes (if run serially)

### Optimization Tips

1. **Cache dependencies:**
   ```yaml
   - uses: actions/cache@v3
     with:
       path: ~/.npm
       key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
   ```

2. **Skip platforms:**
   Remove or comment out build jobs you don't need.

3. **Reduce artifact size:**
   Configure electron-builder to create smaller packages.

---

## Testing Workflows Locally

Use [act](https://github.com/nektos/act) to test workflows locally:

```bash
# Install act
brew install act  # macOS
# or
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Test workflow
act -W .github/workflows/test.yml

# Test release workflow (draft)
act workflow_dispatch -W .github/workflows/draft-release.yml --input version=1.0.0
```

**Note:** Some features (like release creation) won't work locally.

---

## Monitoring

### Notifications

Configure GitHub notifications:
1. Go to: Settings → Notifications
2. Enable "Actions" notifications
3. Choose email or web notifications

### Status Badge

Add to README.md:
```markdown
![Release](https://github.com/YOUR_ORG/BenchMesh/actions/workflows/release-electron.yml/badge.svg)
![Test](https://github.com/YOUR_ORG/BenchMesh/actions/workflows/test.yml/badge.svg)
```

---

## Security

### Workflow Permissions

Workflows use `GITHUB_TOKEN` with these permissions:
- `contents: write` - Create releases, upload assets
- `actions: read` - Read workflow status

### Pull Request Security

PR workflows run with restricted permissions:
- Cannot access secrets
- Cannot push to repository
- Can only read code

### Dependency Security

Keep GitHub Actions up to date:
- `actions/checkout@v4`
- `actions/setup-node@v4`
- `actions/setup-python@v5`

---

## Support

For workflow issues:
1. Check [GitHub Actions documentation](https://docs.github.com/en/actions)
2. Review workflow logs in Actions tab
3. Test locally with `act`
4. Open issue in repository
