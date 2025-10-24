load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_market_data_influx_lib",
    testonly = True,
    srcs = ["test_market_data_influx.py"],
    visibility = ["//system/algo_trader/influx:__pkg__"],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
    ],
)
