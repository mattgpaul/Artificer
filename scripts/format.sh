#!/bin/bash
# Format all Python and BUILD files
# Usage: ./scripts/format.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

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
echo "Run './scripts/lint.sh' to check for any remaining issues."

