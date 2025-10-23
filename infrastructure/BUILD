load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "client",
    srcs = ["client.py"],
    visibility = ["//visibility:public"],
)

# Test target
pytest_test(
    name = "test_client",
    test_lib = "//tests/infrastructure:test_client_lib",
    coverage_path = "infrastructure",
    tags = ["unit"],
)
