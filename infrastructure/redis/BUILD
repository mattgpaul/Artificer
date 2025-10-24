load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis",
    srcs = ["redis.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
)

# Test target
pytest_test(
    name = "test_redis",
    coverage_path = "infrastructure.redis",
    tags = ["unit"],
    test_lib = "//tests/infrastructure/redis:test_redis_lib",
)
