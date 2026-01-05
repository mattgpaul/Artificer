load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/domain:__pkg__",
        "//tests/system/algo_trader/domain:__subpackages__",
    ],
    deps = [
        requirement("pytest"),
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
    ],
)

py_library(
    name = "test_equity_lib",
    testonly = True,
    srcs = ["test_equity.py"],
    visibility = ["//system/algo_trader/domain:__pkg__"],
    deps = [
        requirement("pytest"),
        "//system/algo_trader/domain",
    ],
)

py_library(
    name = "test_portfolio_risk_lib",
    testonly = True,
    srcs = ["test_portfolio_risk.py"],
    visibility = ["//system/algo_trader/domain:__pkg__"],
    deps = [
        requirement("pytest"),
        ":conftest_lib",
        "//system/algo_trader/domain",
    ],
)

py_library(
    name = "test_engine_pause_lib",
    testonly = True,
    srcs = ["test_engine_pause.py"],
    visibility = ["//system/algo_trader/domain:__pkg__"],
    deps = [
        requirement("pytest"),
        ":conftest_lib",
        "//system/algo_trader/domain",
    ],
)
