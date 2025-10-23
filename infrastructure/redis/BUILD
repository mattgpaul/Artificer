load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis",
    srcs = ["redis.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
    visibility = ["//visibility:public"],
)

# Test target
pytest_test(
    name = "test_redis",
    test_lib = "//tests/infrastructure/redis:test_redis_lib",
    coverage_path = "infrastructure.redis",
    tags = ["unit"],
)
