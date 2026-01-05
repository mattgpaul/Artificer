load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "domain",
    srcs = [
        "equity.py",
        "engine.py",
        "events.py",
        "models.py",
        "portfolio.py",
        "strategies.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
        "//tests/system/algo_trader/domain:__pkg__",
    ],
    deps = [
        "//system/algo_trader/ports",
    ],
)

pytest_test(
    name = "test_equity",
    test_lib = "//tests/system/algo_trader/domain:test_equity_lib",
    coverage_path = "system.algo_trader.domain.equity",
    size = "small",
)

pytest_test(
    name = "test_portfolio_risk",
    test_lib = "//tests/system/algo_trader/domain:test_portfolio_risk_lib",
    coverage_path = "system.algo_trader.domain.portfolio",
    size = "small",
)

pytest_test(
    name = "test_engine_pause",
    test_lib = "//tests/system/algo_trader/domain:test_engine_pause_lib",
    coverage_path = "system.algo_trader.domain.engine",
    size = "small",
)
