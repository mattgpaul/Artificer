load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "domain",
    srcs = [
        "engine.py",
        "equity.py",
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
    size = "small",
    coverage_path = "system.algo_trader.domain.equity",
    test_lib = "//tests/system/algo_trader/domain:test_equity_lib",
)

pytest_test(
    name = "test_portfolio_risk",
    size = "small",
    coverage_path = "system.algo_trader.domain.portfolio",
    test_lib = "//tests/system/algo_trader/domain:test_portfolio_risk_lib",
)

pytest_test(
    name = "test_engine_pause",
    size = "small",
    coverage_path = "system.algo_trader.domain.engine",
    test_lib = "//tests/system/algo_trader/domain:test_engine_pause_lib",
)
