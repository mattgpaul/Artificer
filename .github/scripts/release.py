#!/usr/bin/env python3
"""Release script for detecting impacted systems and computing versions."""

import json
import subprocess
import sys


def get_changed_files():
    """Get list of changed files in the current commit."""
    try:
        # Try to get diff from previous commit
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
    except Exception:
        pass

    # Fallback: get all files in current commit
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
    except Exception:
        pass

    return []


def get_latest_tag(system: str) -> str | None:
    """Get the latest version tag for a system."""
    try:
        result = subprocess.run(
            ["git", "tag", "-l", f"{system}/v*"],
            capture_output=True,
            text=True,
            check=True,
        )
        tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
        if not tags:
            return None

        # Sort by version (simple numeric sort)
        def version_key(tag: str) -> tuple[int, int, int]:
            version_str = tag.replace(f"{system}/v", "")
            parts = version_str.split(".")
            return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

        tags.sort(key=version_key, reverse=True)
        return tags[0]
    except Exception:
        return None


def bump_patch_version(version: str) -> str:
    """Bump patch version (X.Y.Z -> X.Y.Z+1)."""
    parts = version.split(".")
    if len(parts) < 3:
        parts.extend(["0"] * (3 - len(parts)))

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    return f"{major}.{minor}.{patch + 1}"


def detect_impacted_systems(changed_files: list[str]) -> dict[str, str]:
    """Detect which systems are impacted and compute their next versions."""
    systems = ["telemetry", "algo_trader"]
    impacted = {}

    for system in systems:
        impacted_flag = False

        # Check if system directory changed
        if any(f.startswith(f"system/{system}/") for f in changed_files):
            impacted_flag = True

        # Check if shared infrastructure changed (affects all systems)
        if any(f.startswith("infrastructure/") for f in changed_files):
            impacted_flag = True

        if impacted_flag:
            latest_tag = get_latest_tag(system)
            if latest_tag:
                version = latest_tag.replace(f"{system}/v", "")
                new_version = bump_patch_version(version)
            else:
                new_version = "0.1.0"

            impacted[system] = new_version

    return impacted


def main():
    """Main entry point."""
    changed_files = get_changed_files()
    impacted = detect_impacted_systems(changed_files)

    # Output as JSON
    output = {
        "impacted": list(impacted.keys()),
        "versions": list(impacted.values()),
        "systems": impacted,
    }

    print(json.dumps(output, indent=2))
    # Important: "no impacted systems" is not an error; it should just be a no-op release.
    return 0


if __name__ == "__main__":
    sys.exit(main())
