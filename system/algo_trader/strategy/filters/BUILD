load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "filters_lib",
    srcs = [
        "base.py",
        "config_loader.py",
        "core.py",
        "filters.py",
        "price_comparison.py",
        "registry.py",
        "sma_comparison.py",
    ],
    data = glob(["strategies/*.yaml"]),
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies/moving_average:moving_average_lib",
        requirement("pandas"),
        requirement("pyyaml"),
    ],
)

# Test targets
pytest_test(
    name = "test_registry",
    size = "small",
    coverage_path = "system.algo_trader.strategy.filters.registry",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/filters:test_registry_lib",
)

pytest_test(
    name = "test_config_loader",
    size = "small",
    coverage_path = "system.algo_trader.strategy.filters.config_loader",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/filters:test_config_loader_lib",
)

pytest_test(
    name = "test_price_comparison",
    size = "small",
    coverage_path = "system.algo_trader.strategy.filters.price_comparison",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/filters:test_price_comparison_lib",
)

pytest_test(
    name = "test_sma_comparison",
    size = "small",
    coverage_path = "system.algo_trader.strategy.filters.sma_comparison",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/filters:test_sma_comparison_lib",
)
