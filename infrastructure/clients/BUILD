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
    name = "influx_client",
    srcs = ["influx_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("python-dotenv"),
        requirement("influxdb3-python"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "schwab_authenticate",
    srcs = ["schwab_client.py"],
    main = "schwab_client.py",
    deps = [
        ":schwab_client",
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "influx_authenticate",
    srcs = ["influx_client.py"],
    main = "influx_client.py",
    deps = [
        ":influx_client",
    ],
    visibility = ["//visibility:public"]
)
