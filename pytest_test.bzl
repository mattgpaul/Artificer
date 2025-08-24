# pytest_test.bzl - Custom pytest macro using pytest-bazel
load("@rules_python//python:defs.bzl", "py_library", "py_test")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("@pip//:requirements.bzl", "requirement")

def pytest_test(name, srcs, **kwargs):
    """
    A clean pytest macro that uses pytest-bazel without requiring
    if __name__ == "__main__" in test files.
    
    Automatically includes common pytest dependencies:
    - pytest
    - pytest-mock  
    - pytest-cov
    - pytest-bazel
    """
    # Extract common arguments
    user_deps = kwargs.pop("deps", [])
    data = kwargs.pop("data", [])
    env = kwargs.pop("env", {})
    
    # Add common pytest dependencies automatically
    common_pytest_deps = [
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-cov"), 
        requirement("pytest-bazel"),
    ]
    
    # Combine user deps with common pytest deps
    all_deps = user_deps + common_pytest_deps
    
    # Create library with test sources
    py_library(
        name = name + ".lib",
        srcs = srcs,
        deps = all_deps,
        data = data,
        testonly = True,
    )

    # Create pytest runner using console script
    py_console_script_binary(
        name = name,
        pkg = "@pip//pytest_bazel",   
        script = "pytest_bazel",      
        binary_rule = py_test,        
        deps = [
            name + ".lib",  
        ],
        data = data + srcs,
        env = env,
        testonly = True,
        args = kwargs.get("args", []) + [
            "$(location :%s)" % src for src in srcs
        ] + ["-v", "-s"],  
        **kwargs,
    )