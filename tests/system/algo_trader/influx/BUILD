load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_market_data_influx_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_market_data_influx.py",
    ],
    visibility = ["//system/algo_trader/influx:__pkg__"],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pyyaml"),
    ],
)

py_library(
    name = "test_publisher_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_publisher.py",
    ],
    visibility = ["//system/algo_trader/influx:__pkg__"],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:publisher_lib",
        "//system/algo_trader/influx/publisher:publisher_modules",
        requirement("pyyaml"),
    ],
)
