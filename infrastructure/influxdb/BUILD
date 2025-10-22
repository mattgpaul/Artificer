load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "influxdb",
    srcs = ["influxdb.py"],
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
    name = "influxdb_authenticate",
    srcs = ["influxdb.py"],
    main = "influxdb.py",
    deps = [
        ":influxdb",
    ],
    visibility = ["//visibility:public"]
)
