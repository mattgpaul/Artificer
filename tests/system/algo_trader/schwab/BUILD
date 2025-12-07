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

