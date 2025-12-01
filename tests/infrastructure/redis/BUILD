load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_redis_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_base_redis_client.py",
        "test_redis_kv_client.py",
        "test_redis_lock_client.py",
        "test_redis_pub_sub_client.py",
        "test_redis_queue_client.py",
        "test_redis_stream_client.py",
    ],
    visibility = ["//infrastructure/redis:__pkg__"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
    ],
)
