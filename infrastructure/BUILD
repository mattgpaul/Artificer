load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "client",
    srcs = ["client.py"],
    visibility = ["//visibility:public"],
)

# Test target
pytest_test(
    name = "test_client",
    coverage_path = "infrastructure",
    tags = ["unit"],
    test_lib = "//tests/infrastructure:test_client_lib",
)
