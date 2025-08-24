# pytest_test.bzl - Custom pytest macro using pytest-bazel
load("@rules_python//python:defs.bzl", "py_library", "py_test")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

def pytest_test(name, srcs, **kwargs):
    """
    A clean pytest macro that uses pytest-bazel without requiring
    if __name__ == "__main__" in test files.
    
    This creates a py_library for the test sources and a py_console_script_binary
    that runs pytest-bazel directly.
    """
    # Extract common arguments
    deps = kwargs.pop("deps", [])
    data = kwargs.pop("data", [])
    env = kwargs.pop("env", {})
    
    # Create library with test sources
    py_library(
        name = name + ".lib",
        srcs = srcs,
        deps = deps,
        data = data,
        testonly = True,
    )

    # Create pytest runner using console script
    py_console_script_binary(
        name = name,
        pkg = "@pip//pytest_bazel",   # pytest-bazel package (using @pip hub)
        script = "pytest_bazel",      # pytest-bazel console script
        binary_rule = py_test,        # Use py_test as the underlying rule
        deps = [
            name + ".lib",  # Include the test library
        ],
        data = data + srcs,
        env = env,
        testonly = True,
        # Pass source files to pytest with verbose output
        args = kwargs.get("args", []) + [
            "$(location :%s)" % src for src in srcs
        ] + ["-v", "-s"],  # Add verbose flags
        **kwargs,
    )
