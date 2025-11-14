load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "process_manager",
    srcs = ["process_manager.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
    ],
)

# Test target
pytest_test(
    name = "test_process_manager",
    size = "small",
    coverage_path = "infrastructure.multiprocess",
    tags = [
        "exclusive",
        "unit",
    ],
    test_lib = "//tests/infrastructure/multiprocess:test_process_manager_lib",
)

