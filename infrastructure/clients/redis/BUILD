load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "market_redis",
    srcs = ["market_redis.py"],
    deps = [
        "//infrastructure/clients:redis_client"
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "test_market_redis",
    srcs = ["market_redis.py"],
    deps = [":market_redis"],
    main = "market_redis.py",
)