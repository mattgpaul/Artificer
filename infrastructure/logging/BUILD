load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "logger",
    srcs = ["logger.py"],
    visibility = ["//visibility:public"],  # Available to entire repo
)

# Test target
pytest_test(
    name = "test_logger",
    coverage_path = "infrastructure.logging",
    tags = ["unit"],
    test_lib = "//tests/infrastructure/logging:test_logger_lib",
)
