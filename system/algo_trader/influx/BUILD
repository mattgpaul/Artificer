load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "influx_services",
    srcs = [
        "market_data_influx.py",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/influxdb:influxdb",
        "//system/algo_trader/utils:schema",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)

py_library(
    name = "market_data_influx",
    srcs = ["market_data_influx.py"],
    deps = [
        "//infrastructure/influxdb:influxdb",
        "//infrastructure/logging:logger",
        requirement("pandas"),
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
)
