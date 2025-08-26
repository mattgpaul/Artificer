load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "stock",
    srcs = ["stock.py"],
    deps = [
        "//component/software/finance:finance", 
        "//infrastructure/client/schwab:schwab_client",
        requirement("pandas"),
    ],
)

# py_binary()

load("//:pytest_test.bzl", "pytest_test")

# Fast unit tests (excludes integration and slow tests)
pytest_test(
    name = "test",
    srcs = ["stock_test.py"],
    coverage_path = "component.software.finance.stock",
    args = ["-m", "not integration and not slow"],
    deps = [
        "//component/software/finance/stock:stock",
        "//component/software/finance:finance",
        requirement("pandas"),
    ],
)

# Integration tests (hits real APIs)
pytest_test(
    name = "test_integration",
    srcs = ["stock_test.py"],
    coverage_path = "component.software.finance.stock",
    args = ["-m", "integration"],
    deps = [
        "//component/software/finance/stock:stock",
        "//component/software/finance:finance",
        requirement("pandas"),
    ],
)

# All tests
pytest_test(
    name = "test_all",
    srcs = ["stock_test.py"],
    coverage_path = "component.software.finance.stock",
    args = ["-m", ""],  # No mark filtering
    deps = [
        "//component/software/finance/stock:stock",
        "//component/software/finance:finance",
        requirement("pandas"),
    ],
)

