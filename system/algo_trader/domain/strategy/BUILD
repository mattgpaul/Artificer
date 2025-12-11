load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "strategy_base",
    srcs = ["strategy.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/domain/strategy:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/domain/strategy/studies:studies_lib",
        requirement("pandas"),
    ],
)

py_library(
    name = "strategy_lib",
    srcs = [
        "journal/calculator.py",
        "journal/efficiency.py",
        "journal/journal.py",
        "journal/trade_matching.py",
        "strategy_registry.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//tests/system/algo_trader/domain/strategy:__subpackages__",  # Allow test access
    ],
    deps = [
        ":strategy_base",
        "//system/algo_trader/domain/strategy/strategies:moving_average_lib",
        requirement("numpy"),
        requirement("pandas"),
    ],
)

pytest_test(
    name = "test_journal",
    size = "small",
    coverage_path = "system.algo_trader.domain.strategy.journal.journal",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/domain/strategy/journal:test_journal_lib",
)

pytest_test(
    name = "test_trade_matching",
    size = "small",
    coverage_path = "system.algo_trader.domain.strategy.journal.trade_matching",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/domain/strategy/journal:test_trade_matching_lib",
)

pytest_test(
    name = "test_sma_crossover",
    size = "small",
    coverage_path = "system.algo_trader.domain.strategy.strategies.sma_crossover",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/domain/strategy/strategies:test_sma_crossover_lib",
)
