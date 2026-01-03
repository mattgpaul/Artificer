load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

# Library for tickers tests
py_library(
    name = "test_tickers_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_tickers.py",
    ],
    visibility = ["//system/algo_trader/datasource/sec:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/sec:tickers_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

# Library for company_facts_config tests
py_library(
    name = "test_company_facts_config_lib",
    testonly = True,
    srcs = ["test_company_facts_config.py"],
    visibility = ["//system/algo_trader/datasource/sec:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/sec:tickers_lib",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)
