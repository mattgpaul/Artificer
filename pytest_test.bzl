# pytest_test.bzl - Working pytest macro that shows output
load("@rules_python//python:defs.bzl", "py_library", "py_test")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("@pip//:requirements.bzl", "requirement")

def pytest_test(name, srcs, coverage_path=None, **kwargs):
    """
    Pytest macro that properly shows test output and pytest details.
    
    Args:
        coverage_path: Path for coverage reporting (e.g., "component.software.finance.stock")
                      If None, will attempt to infer from the target location.
    """
    user_deps = kwargs.pop("deps", [])
    data = kwargs.pop("data", []) + ["//:pytest.ini"]
    env = kwargs.pop("env", {})
    user_args = kwargs.pop("args", [])
    
    common_pytest_deps = [
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-cov"),
        requirement("pytest-bazel"),
    ]
    
    all_deps = user_deps + common_pytest_deps
    
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
    
    # Combine all args properly - user args may contain mark expressions that need to stay together
    args = ["$(location :%s)" % src for src in srcs] + default_pytest_args + user_args
    
    py_library(
        name = name + ".lib",
        srcs = srcs,
        deps = all_deps,
        data = data,
        testonly = True,
    )

    py_console_script_binary(
        name = name,
        pkg = "@pip//pytest_bazel",
        script = "pytest_bazel",
        binary_rule = py_test,
        deps = [name + ".lib"],
        data = data + srcs,
        env = env,
        testonly = True,
        args = args,
        **kwargs,
    )