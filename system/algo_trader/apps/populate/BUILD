load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "populate",
    srcs = ["ohlcv.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//system/algo_trader/infra/schwab:schwab_services",
        "//infrastructure/logging:logger",
    ],
)

py_binary(
    name = "main",
    srcs = ["ohlcv.py"],
    main = "ohlcv.py",
    visibility = ["//visibility:public"],
    deps = [
        ":populate",
    ],
)