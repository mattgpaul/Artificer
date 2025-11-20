load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "strategies",
    srcs = [
        "journal/calculator.py",
        "journal/efficiency.py",
        "journal/journal.py",
        "journal/trade_matching.py",
        "strategies/sma_crossover.py",
        "strategy.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//tests/system/algo_trader/strategy:__subpackages__",  # Allow test access
    ],
    deps = [
        "//system/algo_trader/strategy/studies/moving_average:simple_moving_average",
        "//system/algo_trader/strategy/studies/support_resistance:find_peaks",
        "//system/algo_trader/strategy/studies/support_resistance:find_valleys",
        requirement("numpy"),
        requirement("pandas"),
    ],
)

# Test targets
pytest_test(
    name = "test_journal",
    size = "small",
    coverage_path = "system.algo_trader.strategy.journal.journal",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/strategy/journal:test_journal_lib",
)

pytest_test(
    name = "test_trade_matching",
    size = "small",
    coverage_path = "system.algo_trader.strategy.journal.trade_matching",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/strategy/journal:test_trade_matching_lib",
)

pytest_test(
    name = "test_sma_crossover",
    size = "small",
    coverage_path = "system.algo_trader.strategy.strategies.sma_crossover",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/strategy/strategies:test_sma_crossover_lib",
)
