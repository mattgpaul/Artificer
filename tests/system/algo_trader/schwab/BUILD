load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

# Library for shared test fixtures
py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/schwab:__pkg__",
        "//tests/system/algo_trader/schwab:__subpackages__",
    ],
    deps = [
        requirement("pytest"),
    ],
)

# Library for schwab client tests
py_library(
    name = "test_schwab_client_lib",
    testonly = True,
    srcs = ["test_schwab_client.py"],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/schwab:schwab_services",
    ],
)

# Library for market handler tests
py_library(
    name = "test_market_handler_lib",
    testonly = True,
    srcs = ["test_market_handler.py"],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
)

# Library for account handler tests
py_library(
    name = "test_account_handler_lib",
    testonly = True,
    srcs = ["test_account_handler.py"],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
)

# Library for timescale enum tests
py_library(
    name = "test_timescale_enum_lib",
    testonly = True,
    srcs = ["test_timescale_enum.py"],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
)
