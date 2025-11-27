load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "test_base_lib",
    testonly = True,
    srcs = ["test_base.py"],
    visibility = ["//system/algo_trader/strategy/portfolio_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        "//tests/system/algo_trader/strategy/portfolio_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_fractional_position_size_lib",
    testonly = True,
    srcs = ["test_fractional_position_size.py"],
    visibility = ["//system/algo_trader/strategy/portfolio_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        "//tests/system/algo_trader/strategy/portfolio_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_max_capital_deployed_lib",
    testonly = True,
    srcs = ["test_max_capital_deployed.py"],
    visibility = ["//system/algo_trader/strategy/portfolio_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        "//tests/system/algo_trader/strategy/portfolio_manager:conftest_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_registry_lib",
    testonly = True,
    srcs = ["test_registry.py"],
    visibility = ["//system/algo_trader/strategy/portfolio_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        "//tests/system/algo_trader/strategy/portfolio_manager:conftest_lib",
        requirement("pytest"),
    ],
)

pytest_test(
    name = "test_base",
    size = "small",
    coverage_path = "system.algo_trader.strategy.portfolio_manager.rules",
    tags = ["unit"],
    test_lib = ":test_base_lib",
)

pytest_test(
    name = "test_fractional_position_size",
    size = "small",
    coverage_path = "system.algo_trader.strategy.portfolio_manager.rules",
    tags = ["unit"],
    test_lib = ":test_fractional_position_size_lib",
)

pytest_test(
    name = "test_max_capital_deployed",
    size = "small",
    coverage_path = "system.algo_trader.strategy.portfolio_manager.rules",
    tags = ["unit"],
    test_lib = ":test_max_capital_deployed_lib",
)

pytest_test(
    name = "test_registry",
    size = "small",
    coverage_path = "system.algo_trader.strategy.portfolio_manager.rules",
    tags = ["unit"],
    test_lib = ":test_registry_lib",
)
