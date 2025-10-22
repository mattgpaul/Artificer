#!/usr/bin/env python3
"""
Test runner script for pytest tests in Bazel.
This script runs pytest with the appropriate arguments.
"""
import sys
import subprocess
import os

def main():
    # Get the test file from the first argument
    test_file = sys.argv[1] if len(sys.argv) > 1 else "influx_test.py"
    
    # Find the test file in the runfiles
    import os
    runfiles_dir = os.environ.get('RUNFILES_DIR', '.')
    test_file_path = os.path.join(runfiles_dir, '_main', 'tests', 'infrastructure', test_file)
    
    if not os.path.exists(test_file_path):
        # Fallback to current directory
        test_file_path = test_file
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        test_file_path,
        "-v",  # Verbose output
        "-s",  # Don't capture output
        "--tb=short",  # Short traceback format
    ]
    
    # Add additional arguments if provided
    if len(sys.argv) > 2:
        cmd.extend(sys.argv[2:])
    
    # Run pytest
    result = subprocess.run(cmd, cwd=os.getcwd())
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
