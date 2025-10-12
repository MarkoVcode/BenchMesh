# BenchMesh Documentation

This directory contains the BenchMesh documentation that is:

1. **Embedded in the application** - Displayed in the built-in documentation viewer
2. **Synced to GitHub wiki** - Automatically published when changes are pushed to main
3. **Shipped offline** - Bundled with the application for offline access

## Files

- `Home.md` - Introduction and overview
- `Getting-Started.md` - Installation and first-time setup
- `Configuration.md` - Device configuration guide
- `Automation.md` - Node-RED integration and automation examples
- `API-Reference.md` - REST API documentation (includes embedded Swagger UI in app)

## Editing Documentation

### 1. Edit Markdown Files

Simply edit the `.md` files in this directory using standard GitHub-flavored markdown.

### 2. Update Frontend Copy

After editing, copy the updated files to the frontend:

```bash
# From repository root
cp docs/*.md benchmesh-serial-service/frontend/public/docs/
```

Or use the provided script:

```bash
# From repository root
./scripts/update-docs.sh
```

### 3. Sync to GitHub Wiki

**Automatic (recommended)**: Push changes to the `main` branch. The GitHub Actions workflow will automatically sync to wiki.

**Manual**: Run the sync script:

```bash
# From repository root
./scripts/sync-wiki.sh
```

## Documentation Viewer

The documentation is displayed in-app via a React component (`DocsViewer.tsx`) that:

- Loads markdown files from `/ui/docs/`
- Renders them with `react-markdown` and GitHub-flavored markdown support
- Embeds Swagger UI for the API Reference page
- Provides left sidebar navigation
- Supports internal doc links

To access: Click **📚 Documentation** in the top navigation bar.

## GitHub Wiki Integration

Documentation is automatically synced to the GitHub wiki when:

- Changes to `docs/**/*.md` are pushed to `main` branch
- The sync workflow is manually triggered

The wiki serves as a public-facing documentation site that mirrors the in-app docs.

**Note**: The Swagger UI is only available in the embedded documentation viewer, not on GitHub wiki.

## Markdown Guidelines

- Use GitHub-flavored markdown (GFM)
- Internal doc links: Use page title or ID (e.g., `[Configuration](Configuration)`)
- External links: Use full URLs
- Code blocks: Use triple backticks with language specifier
- Tables: Use GFM table syntax

## File Naming

GitHub wiki requires specific file naming:

- Spaces in filenames become dashes: `Getting Started.md` → `Getting-Started.md`
- Home page must be named `Home.md`

## Testing

After editing documentation:

1. Copy files to frontend: `cp docs/*.md benchmesh-serial-service/frontend/public/docs/`
2. Start the application: `./start.sh`
3. Open documentation viewer: http://localhost:57666 → Click "📚 Documentation"
4. Verify markdown rendering and navigation

## Automation

### Update Script

Create a helper script to copy docs to frontend:

```bash
#!/bin/bash
# scripts/update-docs.sh
cp docs/Home.md docs/Getting-Started.md docs/Configuration.md docs/Automation.md docs/API-Reference.md \
   benchmesh-serial-service/frontend/public/docs/
echo "Documentation updated in frontend/public/docs/"
```

### Build Integration

The frontend build process automatically includes files from `public/docs/` in the distribution.

## Troubleshooting

**Docs not loading in app:**
- Ensure files are copied to `frontend/public/docs/`
- Check browser console for 404 errors
- Verify file names match exactly in `DocsViewer.tsx`

**Wiki sync failing:**
- Check GitHub Actions logs
- Ensure repository has wiki enabled
- Verify GITHUB_TOKEN has wiki write permissions

**Broken internal links:**
- Use exact page titles or IDs from `DocsViewer.tsx`
- Test in both app and wiki

## Contributing

When adding new documentation pages:

1. Create `.md` file in `docs/`
2. Add entry to `DocsViewer.tsx` in `DOC_PAGES` array
3. Copy to `frontend/public/docs/`
4. Update `scripts/sync-wiki.sh` to include new file
5. Test in-app before committing
