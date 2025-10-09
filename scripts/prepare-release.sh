#!/bin/bash

# BenchMesh Release Preparation Script
# This script helps prepare a new release by updating version numbers and creating changelog entries

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if version argument is provided
if [ -z "$1" ]; then
    print_error "Usage: $0 <version>"
    echo "Example: $0 1.0.0"
    exit 1
fi

VERSION=$1

# Validate version format (semantic versioning)
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    print_error "Invalid version format: $VERSION"
    echo "Expected format: MAJOR.MINOR.PATCH[-prerelease]"
    echo "Examples: 1.0.0, 1.0.0-alpha.1, 2.1.3-rc.1"
    exit 1
fi

print_info "Preparing release v$VERSION"

cd "$PROJECT_ROOT"

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    print_warn "You have uncommitted changes. Please commit or stash them first."
    git status -s
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update version in root package.json
print_info "Updating root package.json..."
npm version "$VERSION" --no-git-tag-version

# Update version in electron/package.json
print_info "Updating electron/package.json..."
cd electron
npm version "$VERSION" --no-git-tag-version
cd ..

# Update version in frontend package.json
print_info "Updating frontend/package.json..."
cd benchmesh-serial-service/frontend
npm version "$VERSION" --no-git-tag-version
cd ../..

# Create changelog entry
print_info "Creating CHANGELOG.md entry..."
TODAY=$(date +%Y-%m-%d)
CHANGELOG_ENTRY="## [$VERSION] - $TODAY

### Added
-

### Changed
-

### Fixed
-

### Deprecated
-

### Removed
-

### Security
-
"

# Insert changelog entry after [Unreleased] section
# Create temporary file with the new entry
TEMP_FILE=$(mktemp)
echo "$CHANGELOG_ENTRY" > "$TEMP_FILE"

# Use sed to insert the contents after [Unreleased]
sed -i '/## \[Unreleased\]/r '"$TEMP_FILE" CHANGELOG.md
sed -i '/## \[Unreleased\]/a\\' CHANGELOG.md
rm "$TEMP_FILE"

print_info "Version numbers updated to v$VERSION"
print_info "CHANGELOG.md template created for v$VERSION"

# Show what changed
echo ""
print_info "Modified files:"
git diff --name-only

echo ""
print_warn "Next steps:"
echo "1. Edit CHANGELOG.md and fill in the release notes"
echo "2. Review the changes: git diff"
echo "3. Commit the changes: git commit -am 'Release v$VERSION'"
echo "4. Create and push the tag: git tag v$VERSION && git push origin main --tags"
echo "5. GitHub Actions will automatically build and create the release"

echo ""
print_info "Or create a draft release first for testing:"
echo "Go to: https://github.com/YOUR_ORG/BenchMesh/actions/workflows/draft-release.yml"
echo "Click 'Run workflow' and enter version: $VERSION"
