load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    srcs = ["conftest.py"],
    deps = [
        requirement("pytest"),
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
    ],
    testonly = True,
    visibility = [
        "//system/algo_trader/domain:__pkg__",
        "//tests/system/algo_trader/domain:__subpackages__",
    ],
)

py_library(
    name = "test_equity_lib",
    srcs = ["test_equity.py"],
    deps = [
        requirement("pytest"),
        "//system/algo_trader/domain",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/domain:__pkg__"],
)

py_library(
    name = "test_portfolio_risk_lib",
    srcs = ["test_portfolio_risk.py"],
    deps = [
        requirement("pytest"),
        ":conftest_lib",
        "//system/algo_trader/domain",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/domain:__pkg__"],
)

py_library(
    name = "test_engine_pause_lib",
    srcs = ["test_engine_pause.py"],
    deps = [
        requirement("pytest"),
        ":conftest_lib",
        "//system/algo_trader/domain",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/domain:__pkg__"],
)


