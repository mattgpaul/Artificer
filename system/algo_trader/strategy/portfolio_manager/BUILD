load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "portfolio_manager_lib",
    srcs = [
        "config_loader.py",
        "portfolio_manager.py",
        "rules/base.py",
        "rules/fractional_position_size.py",
        "rules/max_capital_deployed.py",
    ],
    data = glob(["strategies/*.yaml"]),
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        requirement("pandas"),
        requirement("pyyaml"),
    ],
)

# Test targets
pytest_test(
    name = "test_portfolio_manager",
    size = "small",
    coverage_path = "system.algo_trader.strategy.portfolio_manager.portfolio_manager",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/portfolio_manager:test_portfolio_manager_lib",
)

pytest_test(
    name = "test_config_loader",
    size = "small",
    coverage_path = "system.algo_trader.strategy.portfolio_manager.config_loader",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/portfolio_manager:test_config_loader_lib",
)
