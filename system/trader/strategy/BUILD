load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "strategy",
    srcs = [
        "calculation.py",
        "strategy.py",
    ],
    deps = [
        requirement("pandas"),
        requirement("scipy"),
        requirement("numpy"),
    ],
)

# py_binary()

load("//:pytest_test.bzl", "pytest_test")

# Integration tests for calculation functions
pytest_test(
    name = "test_integration",
    srcs = ["calculation_test.py"],
    coverage_path = "system.trader.strategy",
    args = ["-m", "integration"],
    deps = [
        ":strategy",
        "//component/software/finance/stock:stock",
        "//component/software/finance:finance",
        requirement("pandas"),
        requirement("matplotlib"),
    ],
)