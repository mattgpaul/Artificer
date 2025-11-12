load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "sqlite",
    srcs = ["sqlite.py"],
    visibility = [
        "//tests/infrastructure/sqlite:__pkg__",
        "//visibility:public",
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
    ],
)

# Test target
pytest_test(
    name = "test_sqlite",
    coverage_path = "infrastructure.sqlite",
    tags = ["unit"],
    test_lib = "//tests/infrastructure/sqlite:test_sqlite_lib",
)

oci_image(
    name = "sqlite_image_lib",
    base = "@sqlite//:sqlite",
)

oci_load(
    name = "sqlite_image",
    image = ":sqlite_image_lib",
    repo_tags = ["artificer-sqlite:latest"],
)
