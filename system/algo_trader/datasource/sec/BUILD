load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "company_facts_config",
    srcs = ["company_facts_config.py"],
    data = ["company_facts.yaml"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
        "//tests/system/algo_trader/datasource/sec:__pkg__",
    ],
    deps = [
        requirement("pyyaml"),
    ],
)

alias(
    name = "tickers_lib",
    actual = "//system/algo_trader/datasource/sec/tickers:tickers_lib",
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
        "//tests/system/algo_trader/datasource/sec:__pkg__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
)

# Test for Tickers - SEC Ticker Data Retrieval
pytest_test(
    name = "test_tickers",
    size = "small",
    coverage_path = "system.algo_trader.datasource.sec.tickers",
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
