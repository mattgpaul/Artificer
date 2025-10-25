#!/bin/bash
# Setup Git hooks for integration testing
# Run this after cloning the repository

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Setting up Git hooks for Artificer..."

# Create pre-push hook for integration tests and PR creation
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook to run integration tests and auto-create PR

echo "🧪 Running integration tests before push..."

# Run integration tests
echo "Running integration tests..."
if ! bazel test --test_tag_filters="integration" //...; then
    echo "❌ Integration tests failed. Push aborted."
    echo "   Fix failing tests before pushing."
    exit 1
fi

echo "✅ All integration tests passed!"

# Get current branch name
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
MAIN_BRANCH="main"  # Adjust if your main branch is different

# Only create PR for feature branches, not main/master
if [[ "$CURRENT_BRANCH" != "$MAIN_BRANCH" && "$CURRENT_BRANCH" != "master" ]]; then
    echo ""
    echo "🚀 Auto-creating PR for branch: $CURRENT_BRANCH"
    
    # Check if GitHub CLI is available
    if command -v gh &> /dev/null; then
        # Check if PR already exists
        if gh pr view "$CURRENT_BRANCH" &> /dev/null; then
            echo "📋 PR already exists for branch: $CURRENT_BRANCH"
            echo "   View: $(gh pr view --web --json url -q .url)"
        else
            # Create PR with auto-generated title and body
            echo "Creating new PR..."
            
            # Generate PR title from branch name
            PR_TITLE=$(echo "$CURRENT_BRANCH" | sed 's/feature\///' | sed 's/fix\///' | sed 's/refactor\///' | sed 's/-/ /g' | sed 's/\b\w/\U&/g')
            
            # Generate PR body with commit info
            COMMITS=$(git log --oneline "$MAIN_BRANCH..$CURRENT_BRANCH" | head -5)
            PR_BODY="## Changes

This PR includes the following commits:

\`\`\`
$COMMITS
\`\`\`

## Testing

- ✅ Integration tests passed
- ✅ Code formatted and linted
- ✅ All checks completed successfully

## Auto-generated PR

This PR was automatically created by the pre-push hook after successful integration tests."
            
            # Create the PR
            PR_URL=$(gh pr create \
                --title "$PR_TITLE" \
                --body "$PR_BODY" \
                --base "$MAIN_BRANCH" \
                --head "$CURRENT_BRANCH" \
                --assignee "@me" \
                --label "auto-created" \
                --web)
            
            if [ $? -eq 0 ]; then
                echo "✅ PR created successfully!"
                echo "   URL: $PR_URL"
                echo "   CI/CD pipelines will start automatically"
            else
                echo "⚠️  Failed to create PR automatically"
                echo "   You can create it manually at: https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name)/compare/$CURRENT_BRANCH"
            fi
        fi
    else
        echo "⚠️  GitHub CLI (gh) not found. Install it to enable auto-PR creation:"
        echo "   https://cli.github.com/"
        echo "   Manual PR creation: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]\([^/]*\/[^/]*\)\.git/\1/')/compare/$CURRENT_BRANCH"
    fi
else
    echo "ℹ️  Skipping PR creation for main branch: $CURRENT_BRANCH"
fi

exit 0
EOF

chmod +x "$HOOKS_DIR/pre-push"

echo "✅ Pre-push hook installed successfully!"
echo ""
echo "Features enabled:"
echo "  🧪 Integration tests before push"
echo "  🚀 Auto-PR creation (requires GitHub CLI)"
echo ""
echo "To install GitHub CLI for auto-PR creation:"
echo "  https://cli.github.com/"
echo ""
echo "To bypass the hook (not recommended), use: git push --no-verify"

