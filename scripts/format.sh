#!/bin/bash
# Format all Python and BUILD files
# Usage: bazel run //:format

set -e

# Change to workspace root (Bazel provides this)
cd "$BUILD_WORKSPACE_DIRECTORY"

echo "📝 Formatting all code files..."
echo ""

echo "=== Formatting Python with ruff ==="
bazel run //:ruff -- format .
bazel run //:ruff -- check . --fix

echo ""
echo "=== Formatting BUILD files with buildifier ==="
bazel run //:buildifier -- -r .

echo ""
echo "✅ Formatting complete!"
echo ""
echo "Run 'bazel run //:lint' to check for any remaining issues."

