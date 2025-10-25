#!/bin/bash
# Setup Git hooks for integration testing
# Run this after cloning the repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Setting up Git hooks for Artificer..."

# Create pre-push hook for integration tests
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook to run integration tests before pushing

echo "🧪 Running integration tests before push..."

# Run integration tests
echo "Running integration tests..."
if ! bazel test --test_tag_filters=integration; then
    echo "❌ Integration tests failed. Push aborted."
    echo "   Fix failing tests before pushing."
    exit 1
fi

echo "✅ All integration tests passed!"
exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"

echo "✅ Pre-push hook installed successfully!"
echo ""
echo "To bypass the hook (not recommended), use: git push --no-verify"

