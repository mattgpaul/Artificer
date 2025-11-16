load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "fundamentals_lib",
    srcs = [
        "handler.py",
        "processor.py",
        "utils.py",
    ],
    visibility = [
        "//system/algo_trader/datasource:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__subpackages__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
        "//system/algo_trader/datasource/populate:argument_base",
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/mysql:bad_ticker_client",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/strategy:cli_utils",
        requirement("pandas"),
    ],
)
