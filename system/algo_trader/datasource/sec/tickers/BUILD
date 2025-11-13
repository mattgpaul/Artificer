load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "tickers_lib",
    srcs = [
        "dataframe.py",
        "main.py",
        "sic.py",
        "static.py",
    ],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
        "//tests/system/algo_trader/datasource/sec:__pkg__",
        "//tests/system/algo_trader/strategy:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/datasource/sec:company_facts_config",
        requirement("pandas"),
        requirement("requests"),
    ],
)
