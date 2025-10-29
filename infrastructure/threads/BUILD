load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "thread_manager",
    srcs = ["thread_manager.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
    ],
)

# Test target
pytest_test(
    name = "test_thread_manager",
    coverage_path = "infrastructure.threads",
    tags = ["unit", "exclusive"],
    args = ["--local_test_jobs=1"]
    size = "small",
    test_lib = "//tests/infrastructure/threads:test_thread_manager_lib",
)
