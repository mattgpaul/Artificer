load("@rules_python//python:defs.bzl", "py_library")

# Library for schwab client tests
py_library(
    name = "test_schwab_client_lib",
    srcs = ["test_schwab_client.py"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/schwab:__pkg__"],
)

# Library for market handler tests
py_library(
    name = "test_market_handler_lib",
    srcs = ["test_market_handler.py"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/schwab:__pkg__"],
)

# Library for account handler tests
py_library(
    name = "test_account_handler_lib",
    srcs = ["test_account_handler.py"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/schwab:__pkg__"],
)

# Library for timescale enum tests
py_library(
    name = "test_timescale_enum_lib",
    srcs = ["test_timescale_enum.py"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/schwab:__pkg__"],
)
