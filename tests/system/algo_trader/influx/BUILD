load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/influx:__pkg__",
        "//tests/system/algo_trader/influx:__subpackages__",
    ],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)

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

py_library(
    name = "test_diagnose_missing_data_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_diagnose_missing_data.py",
    ],
    visibility = ["//system/algo_trader/influx:__pkg__"],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//infrastructure/mysql",
        "//system/algo_trader/influx:diagnose_missing_data",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
    ],
)
