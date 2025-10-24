#!/bin/bash
# Manual linting script for checking code quality
# Usage: ./scripts/lint.sh [path]

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TARGET="${1:-.}"  # Default to current directory if no argument

echo "🔍 Linting Python files in $TARGET..."
echo ""

# Run ruff check
echo "=== Ruff Lint Check ==="
bazel run //:ruff -- check "$TARGET"
RUFF_EXIT=$?

echo ""
echo "=== Buildifier Lint Check ==="
bazel run //:buildifier -- -lint=warn -mode=check -r "$TARGET"
BUILDIFIER_EXIT=$?

echo ""
if [ $RUFF_EXIT -eq 0 ] && [ $BUILDIFIER_EXIT -eq 0 ]; then
    echo "✅ All lint checks passed!"
    exit 0
else
    echo "❌ Lint checks failed. Run these to fix:"
    [ $RUFF_EXIT -ne 0 ] && echo "   bazel run //:ruff -- check . --fix"
    [ $BUILDIFIER_EXIT -ne 0 ] && echo "   bazel run //:buildifier -- -r ."
    exit 1
fi

