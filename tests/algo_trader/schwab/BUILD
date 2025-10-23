load("//:pytest_test.bzl", "pytest_test")
load("@pip//:requirements.bzl", "requirement")

pytest_test(
    name = "test_schwab_client",
    srcs = ["test_schwab_client.py"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
    coverage_path = "system.algo_trader.schwab.schwab_client",
)

pytest_test(
    name = "test_market_handler",
    srcs = ["test_market_handler.py"],
    deps = [
        "//system/algo_trader/schwab:schwab_services",
    ],
    coverage_path = "system.algo_trader.schwab.market_handler",
)
