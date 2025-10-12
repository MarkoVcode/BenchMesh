#!/bin/bash
# Sync documentation from docs/ to GitHub wiki
# This script clones the wiki repository and syncs markdown files
#
# Usage:
#   ./scripts/sync-wiki.sh                                    # Auto-detect from git remote
#   ./scripts/sync-wiki.sh git@github.com:user/repo.wiki.git # Specify wiki URL

set -e

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs"
TEMP_WIKI_DIR="/tmp/benchmesh-wiki-$$"

# Auto-detect wiki URL from git remote if not provided
if [ -z "$1" ]; then
  # Get the main repository URL from git remote
  MAIN_REPO=$(git -C "$DOCS_DIR/.." remote get-url origin 2>/dev/null || echo "")

  if [ -z "$MAIN_REPO" ]; then
    echo "❌ Error: Could not detect git repository."
    echo "Usage: $0 <wiki-repository-url>"
    echo "Example: $0 git@github.com:youruser/yourrepo.wiki.git"
    exit 1
  fi

  # Convert main repo URL to wiki URL
  # Handle both SSH and HTTPS URLs
  if [[ "$MAIN_REPO" =~ ^git@github.com:(.+)\.git$ ]]; then
    # SSH format: git@github.com:user/repo.git -> git@github.com:user/repo.wiki.git
    REPO_URL="git@github.com:${BASH_REMATCH[1]}.wiki.git"
  elif [[ "$MAIN_REPO" =~ ^https://github.com/(.+)\.git$ ]]; then
    # HTTPS format: https://github.com/user/repo.git -> https://github.com/user/repo.wiki.git
    REPO_URL="https://github.com/${BASH_REMATCH[1]}.wiki.git"
  elif [[ "$MAIN_REPO" =~ ^https://github.com/(.+)$ ]]; then
    # HTTPS without .git: https://github.com/user/repo -> https://github.com/user/repo.wiki.git
    REPO_URL="https://github.com/${BASH_REMATCH[1]}.wiki.git"
  else
    echo "❌ Error: Could not parse repository URL: $MAIN_REPO"
    echo "Please specify wiki URL manually:"
    echo "Usage: $0 <wiki-repository-url>"
    exit 1
  fi

  echo "🔍 Auto-detected wiki URL from git remote"
else
  REPO_URL="$1"
fi

echo "📚 Syncing documentation to GitHub wiki..."
echo "Repository: $REPO_URL"
echo "Source: $DOCS_DIR"

# Clone wiki repository
echo "Cloning wiki repository..."
git clone "$REPO_URL" "$TEMP_WIKI_DIR"

# Copy markdown files (excluding non-wiki files)
echo "Copying documentation files..."
cp "$DOCS_DIR/Home.md" "$TEMP_WIKI_DIR/"
cp "$DOCS_DIR/Getting-Started.md" "$TEMP_WIKI_DIR/"
cp "$DOCS_DIR/Configuration.md" "$TEMP_WIKI_DIR/"
cp "$DOCS_DIR/Automation.md" "$TEMP_WIKI_DIR/"
cp "$DOCS_DIR/API-Reference.md" "$TEMP_WIKI_DIR/"

# Navigate to wiki directory
cd "$TEMP_WIKI_DIR"

# Check if there are changes
if git diff --quiet && git diff --cached --quiet; then
  echo "✅ No changes detected. Wiki is up to date."
  rm -rf "$TEMP_WIKI_DIR"
  exit 0
fi

# Commit and push changes
echo "Committing changes..."
git add *.md
git commit -m "Update documentation from main repository"

echo "Pushing to wiki..."
git push origin master

# Cleanup
cd -
rm -rf "$TEMP_WIKI_DIR"

echo "✅ Documentation synced successfully!"
