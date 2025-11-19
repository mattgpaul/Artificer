load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_journal_lib",
    testonly = True,
    srcs = ["test_journal.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//system/algo_trader/strategy:strategies",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_trade_matching_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_trade_matching.py",
    ],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//system/algo_trader/strategy:strategies",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
