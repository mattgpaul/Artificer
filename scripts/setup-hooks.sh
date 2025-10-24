#!/bin/bash
# Setup Git hooks for code quality enforcement
# Run this after cloning the repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Setting up Git hooks for Artificer..."

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook to enforce code quality standards

echo "🔍 Running code quality checks..."

# Get list of Python files being committed
PYTHON_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -n "$PYTHON_FILES" ]; then
    echo "📝 Formatting Python files with ruff..."
    bazel run //:ruff -- format $PYTHON_FILES
    
    echo "🔍 Linting Python files with ruff..."
    bazel run //:ruff -- check $PYTHON_FILES --fix
    
    # Re-add files that were formatted
    git add $PYTHON_FILES
    
    # Check for remaining errors
    if ! bazel run //:ruff -- check $PYTHON_FILES; then
        echo "❌ Ruff found issues that need manual fixing. Commit aborted."
        echo "   Run: bazel run //:format"
        exit 1
    fi
fi

# Get list of BUILD files being committed
BUILD_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep 'BUILD$\|\.bzl$')

if [ -n "$BUILD_FILES" ]; then
    echo "📝 Formatting BUILD files with buildifier..."
    bazel run //:buildifier -- $BUILD_FILES
    
    # Re-add formatted BUILD files
    git add $BUILD_FILES
fi

echo "✅ All checks passed!"
exit 0
EOF

chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Pre-commit hook installed successfully!"
echo ""
echo "To bypass the hook (not recommended), use: git commit --no-verify"

