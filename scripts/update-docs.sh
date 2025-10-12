#!/bin/bash
# Update documentation in frontend from docs/ directory
# Run this after editing docs/*.md files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_DIR="$REPO_ROOT/docs"
FRONTEND_DOCS_DIR="$REPO_ROOT/benchmesh-serial-service/frontend/public/docs"

echo "📚 Updating frontend documentation..."
echo "Source: $DOCS_DIR"
echo "Target: $FRONTEND_DOCS_DIR"

# Create target directory if it doesn't exist
mkdir -p "$FRONTEND_DOCS_DIR"

# Copy documentation files
cp "$DOCS_DIR/Home.md" "$FRONTEND_DOCS_DIR/"
cp "$DOCS_DIR/Getting-Started.md" "$FRONTEND_DOCS_DIR/"
cp "$DOCS_DIR/Configuration.md" "$FRONTEND_DOCS_DIR/"
cp "$DOCS_DIR/Automation.md" "$FRONTEND_DOCS_DIR/"
cp "$DOCS_DIR/API-Reference.md" "$FRONTEND_DOCS_DIR/"

echo "✅ Documentation updated successfully!"
echo ""
echo "Files copied:"
ls -lh "$FRONTEND_DOCS_DIR"/*.md
echo ""
echo "Next steps:"
echo "  1. Test in app: ./start.sh"
echo "  2. Commit changes to sync to GitHub wiki"
