#!/bin/bash
set -e

# Get latest tag, default to v0.0.0 if none
latest=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Latest tag: $latest"

# Parse version numbers (strip 'v' prefix)
v=${latest#v}
IFS='.' read -r maj min pat <<< "$v"
maj=${maj:-0}; min=${min:-0}; pat=${pat:-0}

# Increment patch
new_tag="v${maj}.${min}.$((pat + 1))"
echo "Creating tag: $new_tag"

git tag "$new_tag"
echo "Done: $new_tag"
