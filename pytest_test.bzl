load("@pip//:requirements.bzl", "requirement")

# pytest_test.bzl - Working pytest macro that shows output
load("@rules_python//python:defs.bzl", "py_test")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

def pytest_test(name, test_lib, coverage_path = None, **kwargs):
    """
    Pytest macro that properly shows test output and pytest details.

    Requires explicit py_library definitions for test code:
    1. Define py_library with test source files and implementation deps
    2. Pass that library target as test_lib parameter
    3. Macro adds pytest dependencies and creates test target

    Args:
        name: Name of the test target
        test_lib: Label of the py_library containing test code
        coverage_path: Path for coverage reporting (e.g., "system.algo_trader.schwab")
        deps: Additional dependencies beyond test_lib
        **kwargs: Additional arguments passed to py_test
    """
    user_deps = kwargs.pop("deps", [])
    data = kwargs.pop("data", [])
    env = kwargs.pop("env", {})
    user_args = kwargs.pop("args", [])

    common_pytest_deps = [
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-cov"),
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
