load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "strategy",
    srcs = [
        "calculation.py",
        "config.py",
        "strategy.py",
    ],
    deps = [
        "//component/software/finance/stock:stock",
        "//infrastructure/logging:logging",
        requirement("pandas"),
        requirement("scipy"),
        requirement("numpy"),
    ],
)

# py_binary()

# load("//:pytest_test.bzl", "pytest_test")

# # Integration tests for calculation functions
# pytest_test(
#     name = "test_integration",
#     srcs = ["calculation_test.py"],
#     coverage_path = "system.trader.strategy",
#     args = ["-m", "integration"],
#     deps = [
#         ":strategy",
#         "//component/software/finance/stock:stock",
#         "//component/software/finance:finance",
#         requirement("pandas"),
#         requirement("matplotlib"),
#     ],
# )