load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "publisher_modules",
    srcs = [
        "config.py",
        "queue_processor.py",
    ],
    visibility = [
        "//system/algo_trader/influx:__pkg__",
        "//tests/system/algo_trader/influx:__pkg__",
    ],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/redis:redis_services",
        requirement("pyyaml"),
    ],
)

py_library(
    name = "publisher_service",
    srcs = [
        "publisher.py",
    ],
    visibility = [
        "//system/algo_trader/influx:__pkg__",
        "//tests/system/algo_trader/influx:__pkg__",
    ],
    deps = [
        ":publisher_modules",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        requirement("pyyaml"),
    ],
)
