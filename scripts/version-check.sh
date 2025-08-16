#!/bin/bash
# Version consistency checker
# Ensures all version numbers are synchronized across files

set -e

echo "🔍 Checking version consistency..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Check that Cargo.toml version matches VERSION file
check_service_version() {
    local service_path=$1
    local service_name=$(basename "$service_path")
    
    if [[ ! -f "$service_path/Cargo.toml" || ! -f "$service_path/VERSION" ]]; then
        echo -e "${YELLOW}⚠️  Skipping $service_name (missing files)${NC}"
        return 0
    fi
    
    local cargo_version=$(grep '^version = ' "$service_path/Cargo.toml" | sed 's/version = "\(.*\)"/\1/')
    local version_file=$(cat "$service_path/VERSION" | tr -d '\n\r')
    
    if [[ "$cargo_version" != "$version_file" ]]; then
        echo -e "${RED}❌ $service_name: Version mismatch${NC}"
        echo "   Cargo.toml: $cargo_version"
        echo "   VERSION file: $version_file"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✅ $service_name: Versions match ($cargo_version)${NC}"
    fi
}

# Check all services
for service_dir in services/*/; do
    if [[ -d "$service_dir" ]]; then
        check_service_version "$service_dir"
    fi
done

# Check if CHANGELOG.md was updated for version changes
check_changelog() {
    echo ""
    echo "📝 Checking CHANGELOG.md..."
    
    if [[ ! -f "CHANGELOG.md" ]]; then
        echo -e "${RED}❌ CHANGELOG.md not found${NC}"
        ERRORS=$((ERRORS + 1))
        return
    fi
    
    # Check if there are uncommitted changes in services but no CHANGELOG update
    if git diff --quiet HEAD -- services/; then
        echo -e "${GREEN}✅ No service changes detected${NC}"
    else
        if git diff --quiet HEAD -- CHANGELOG.md; then
            echo -e "${YELLOW}⚠️  Service changes detected but CHANGELOG.md not updated${NC}"
            echo "   Consider updating CHANGELOG.md to document your changes"
        else
            echo -e "${GREEN}✅ CHANGELOG.md has been updated${NC}"
        fi
    fi
}

check_changelog

# Check for dependency version ranges (should be exact pins)
check_dependency_pinning() {
    echo ""
    echo "📌 Checking dependency pinning..."
    
    local found_ranges=0
    
    for cargo_file in services/*/Cargo.toml; do
        if [[ -f "$cargo_file" ]]; then
            local service_name=$(basename "$(dirname "$cargo_file")")
            
            # Look for version ranges in [dependencies] section only (^, ~, or missing =)
            # Skip the [package] section which doesn't need = prefix
            if awk '/^\[dependencies\]/,/^\[/ { if (/^[^[]/ && /version = "[^=]/) print }' "$cargo_file" | grep -q .; then
                echo -e "${RED}❌ $service_name: Found version ranges in dependencies${NC}"
                echo "   Use exact versions like: version = \"=1.2.3\""
                echo "   Found ranges:"
                awk '/^\[dependencies\]/,/^\[/ { if (/^[^[]/ && /version = "[^=]/) print "     " $0 }' "$cargo_file"
                found_ranges=1
                ERRORS=$((ERRORS + 1))
            fi
        fi
    done
    
    if [[ $found_ranges -eq 0 ]]; then
        echo -e "${GREEN}✅ All dependencies use exact version pinning${NC}"
    fi
}

check_dependency_pinning

# Summary
echo ""
echo "📊 Version Check Summary:"
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}✅ All version checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS version inconsistencies${NC}"
    echo ""
    echo "Fix the issues above before committing."
    echo "See .cursor/rules/versioning-guide.mdc for detailed guidance."
    exit 1
fi
