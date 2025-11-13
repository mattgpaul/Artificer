load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "tickers_lib",
    srcs = [
        "company_facts_config.py",
        "tickers.py",
    ],
    data = ["company_facts.yaml"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",  # Allow populate tests to access tickers
        "//tests/system/algo_trader/datasource/sec:__pkg__",
        "//tests/system/algo_trader/strategy:__pkg__",  # Allow strategy tests to access tickers
    ],
    deps = [
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("pandas"),
        requirement("pyyaml"),
    ],
)

# Test for Tickers - SEC Ticker Data Retrieval
pytest_test(
    name = "test_tickers",
    size = "small",
    coverage_path = "system.algo_trader.datasource.sec",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/sec:test_tickers_lib",
)

# Test for Company Facts Config
pytest_test(
    name = "test_company_facts_config",
    size = "small",
    coverage_path = "system.algo_trader.datasource.sec.company_facts_config",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/sec:test_company_facts_config_lib",
)
