load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_market_data_influx_lib",
    srcs = ["test_market_data_influx.py"],
    deps = [
        "//system/algo_trader/influx:market_data_influx",
        "//infrastructure/influxdb:influxdb",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/influx:__pkg__"],
)

