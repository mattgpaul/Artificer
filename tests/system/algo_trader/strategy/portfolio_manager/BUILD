load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_portfolio_manager_lib",
    testonly = True,
    srcs = ["test_portfolio_manager.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)


