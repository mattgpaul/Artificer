"""Pytest test macro for Bazel with output visibility and coverage support.

This module provides a pytest_test macro that creates properly configured
py_test targets with pytest dependencies and coverage reporting.
"""

load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library", "py_test")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

def pytest_test(name, test_lib = None, coverage_path = None, **kwargs):
    """Create a pytest test target with proper configuration.

    Requires explicit py_library definitions for test code:
    1. Define py_library with test source files and implementation deps
    2. Pass that library target as test_lib parameter
    3. Macro adds pytest dependencies and creates test target

    Args:
        name: Name of the test target.
        test_lib: Optional label of the py_library containing test code. If omitted,
            this macro will create a private py_library from the provided srcs/deps.
        coverage_path: Optional path for coverage reporting (e.g., "system.algo_trader.schwab").
        **kwargs: Additional arguments passed to py_test (e.g., deps, data, env, args).
    """
    user_deps = kwargs.pop("deps", [])
    srcs = kwargs.pop("srcs", [])
    data = kwargs.pop("data", [])
    env = kwargs.pop("env", {})
    user_args = kwargs.pop("args", [])

    common_pytest_deps = [
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-cov"),
        requirement("pytest-timeout"),
        requirement("pytest-bazel"),
    ]

    # Build pytest args with coverage and verbosity by default
    default_pytest_args = [
        "-v",  # Verbose output
        "-s",  # Don't capture output (show print statements)
        "--tb=short",  # Short traceback format
        "--cov-report=term-missing",  # Show missing lines in terminal
        "--cov-report=html:htmlcov",  # Generate HTML coverage report
    ]

    # Add coverage path if specified
    if coverage_path:
        default_pytest_args.append("--cov=" + coverage_path)

    # Let pytest auto-discover tests from the library
    # Use --pyargs to run tests by module name
    args = default_pytest_args + user_args

    # Back-compat: allow BUILD files to provide srcs/deps directly.
    # If test_lib isn't provided, synthesize a test-only library target.
    if not test_lib:
        if not srcs:
            fail("pytest_test(%s): must provide either test_lib=... or srcs=[...]" % name)
        test_lib_name = name + "_lib"
        py_library(
            name = test_lib_name,
            srcs = srcs,
            deps = user_deps,
            testonly = True,
            visibility = ["//visibility:private"],
        )
        test_lib = ":" + test_lib_name
        user_deps = []

    # Build dependency list: test_lib + any additional user deps + pytest deps
    test_deps = [test_lib] + user_deps + common_pytest_deps

    py_console_script_binary(
        name = name,
        pkg = "@pip//pytest_bazel",
        script = "pytest_bazel",
        binary_rule = py_test,
        deps = test_deps,
        data = data,
        env = env,
        testonly = True,
        args = args,
        **kwargs
    )
