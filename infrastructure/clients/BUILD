load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis",
    srcs = ["redis.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "schwab",
    srcs = ["schwab.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "influx",
    srcs = ["influx.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("pandas"),
        requirement("influxdb3-python"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "schwab_authenticate",
    srcs = ["schwab.py"],
    main = "schwab.py",
    deps = [
        ":schwab",
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "influx_authenticate",
    srcs = ["influx.py"],
    main = "influx.py",
    deps = [
        ":influx",
    ],
    visibility = ["//visibility:public"]
)
