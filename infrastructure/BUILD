load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "config",
    srcs = ["config.py"],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pydantic"),
        requirement("pydantic-settings"),
    ],
)

py_library(
    name = "client",
    srcs = ["client.py"],
    visibility = ["//visibility:public"],
    deps = [
        ":config",
    ],
)

# Test targets
pytest_test(
    name = "test_client",
    coverage_path = "infrastructure",
    tags = ["unit"],
    test_lib = "//tests/infrastructure:test_client_lib",
)

pytest_test(
    name = "test_config",
    coverage_path = "infrastructure.config",
    tags = ["unit"],
    test_lib = "//tests/infrastructure:test_config_lib",
)
