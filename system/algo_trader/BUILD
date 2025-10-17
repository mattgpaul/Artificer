load("@pip//:requirements.bzl", "requirement")

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [
        "//system/algo_trader/clients:redis_client",
        "//system/algo_trader/clients:schwab_client",
        "//system/algo_trader/clients:influxdb_client",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//visibility:public"],
)

