load("@pip//:requirements.bzl", "requirement")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis",
    srcs = [
        "base_redis_client.py",
        "redis_kv_client.py",
        "redis_lock_client.py",
        "redis_pub_sub_client.py",
        "redis_queue_client.py",
        "redis_stream_client.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
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

oci_image(
    name = "redis_image_lib",
    base = "@redis//:redis",
)

oci_load(
    name = "redis_image",
    image = ":redis_image_lib",
    repo_tags = ["artificer-redis:latest"],
)
