#!/bin/bash
# Setup Git hooks for integration testing
# Run this after cloning the repository
# 
# This script configures pre-push hooks that run integration tests
# and guides users to GitHub's native PR creation workflow.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Setting up Git hooks for Artificer..."

# Create pre-push hook for code quality checks and integration tests
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook to run code quality checks before pushing

echo "🔍 Running code quality checks before push..."

# Run formatting
echo "📝 Formatting code..."
if ! bazel run //:format; then
    echo "❌ Formatting failed. Push aborted."
    exit 1
fi

# Run linting
echo "🔍 Linting code..."
if ! bazel run //:lint; then
    echo "❌ Linting failed. Push aborted."
    echo "   Fix linting issues before pushing."
    exit 1
fi

echo "✅ Code quality checks passed!"
echo ""

# Run integration tests
echo "🧪 Running integration tests..."
# Use Bazel tags to select test targets, and pytest marks to filter test functions
# Bazel tags filter which test targets to run (BUILD file tags)
# Pytest marks filter which test functions to run within those targets (@pytest.mark.integration)
if ! bazel test --test_tag_filters="integration" --test_arg="-m" --test_arg="integration" //...; then
    echo "❌ Integration tests failed. Push aborted."
    echo "   Fix failing tests before pushing."
    exit 1
fi

echo "✅ All integration tests passed!"
echo ""

# Run e2e tests
echo "🧪 Running end-to-end (e2e) tests..."
# Use Bazel tags to select test targets, and pytest marks to filter test functions
if ! bazel test --test_tag_filters="e2e" --test_arg="-m" --test_arg="e2e" //...; then
    echo "❌ E2E tests failed. Push aborted."
    echo "   Fix failing tests before pushing."
    exit 1
fi

echo "✅ All e2e tests passed!"
echo ""

# Check if any changes were made and amend commit if necessary
if [ -n "$(git diff HEAD)" ]; then
    echo "📝 Committing formatting/linting changes..."
    git add -A
    git commit --amend --no-edit
    echo "✅ Changes committed to current commit"
fi

echo "💡 After push, GitHub will show a 'Create Pull Request' button"
echo "   Click it to create PR and trigger CI/CD pipelines automatically"
exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"

echo "✅ Pre-push hook installed successfully!"
echo ""
echo "Features enabled:"
echo "  📝 Code formatting with ruff"
echo "  🔍 Code linting with ruff"
echo "  🧪 Integration tests (tagged with 'integration' in BUILD files)"
echo "  🧪 E2E tests (tagged with 'e2e' in BUILD files)"
echo "  💡 GitHub's native 'Create Pull Request' button after push"
echo ""
echo "To bypass the hook (not recommended), use: git push --no-verify"

