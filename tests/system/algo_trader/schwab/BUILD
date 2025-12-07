load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_schwab_client_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_schwab_client.py",
    ],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
        requirement("pytest"),
        requirement("requests"),
    ],
)


py_library(
    name = "test_account_handler_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_account_handler.py",
    ],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
        requirement("pytest"),
        requirement("requests"),
    ],
)


py_library(
    name = "test_market_handler_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_market_handler.py",
    ],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
        requirement("pytest"),
        requirement("requests"),
    ],
)


py_library(
    name = "test_timescale_enum_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_timescale_enum.py",
    ],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
        requirement("pytest"),
    ],
)


py_library(
    name = "test_token_manager_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_token_manager.py",
    ],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
        requirement("pytest"),
        requirement("requests"),
    ],
)


py_library(
    name = "test_oauth2_handler_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_oauth2_handler.py",
    ],
    visibility = ["//system/algo_trader/schwab:__pkg__"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
        requirement("pytest"),
        requirement("requests"),
    ],
)



