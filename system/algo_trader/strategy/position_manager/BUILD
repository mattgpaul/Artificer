load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "position_manager_lib",
    srcs = [
        "config_loader.py",
        "position_manager.py",
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
    name = "test_position_manager",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.position_manager",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/position_manager:test_position_manager_lib",
)

pytest_test(
    name = "test_config_loader",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.config_loader",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/position_manager:test_config_loader_lib",
)
