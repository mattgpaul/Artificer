load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/strategy/portfolio_manager:__pkg__",
        "//tests/system/algo_trader/strategy/portfolio_manager:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_portfolio_manager_lib",
    testonly = True,
    srcs = ["test_portfolio_manager.py"],
    visibility = ["//system/algo_trader/strategy/portfolio_manager:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_config_loader_lib",
    testonly = True,
    srcs = ["test_config_loader.py"],
    visibility = ["//system/algo_trader/strategy/portfolio_manager:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)
