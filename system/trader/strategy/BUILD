load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "strategy",
    srcs = [
        "calculation.py",
        "strategy.py",
    ],
    deps = [
        "//component/software/finance/stock:stock",
        "//infrastructure/logging:logger",
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
        requirement("pandas"),
        requirement("numpy"),
        requirement("matplotlib"),
        requirement("scipy"),
    ],
)