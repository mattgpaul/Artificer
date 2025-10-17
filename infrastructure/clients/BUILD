load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "redis_client",
    srcs = ["redis_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "schwab_client",
    srcs = ["schwab_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("python-dotenv"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "influxdb_client",
    srcs = ["influxdb_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("influxdb3-python"),
    ],
    visibility = ["//visibility:public"],
)