load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "ohlcv_lib",
    srcs = [
        "handler.py",
        "processor.py",
        "verifier.py",
    ],
    visibility = [
        "//system/algo_trader/domain/datasource:__subpackages__",
        "//tests/system/algo_trader/domain/datasource/populate:__subpackages__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
        # TODO: Update when engine is rewritten - was: "//system/algo_trader/backtest:cli_utils",
        "//system/algo_trader/domain/datasource/populate:argument_base",
        "//system/algo_trader/domain/datasource/sec/tickers:tickers_lib",
        "//system/algo_trader/infra/database/mysql:bad_ticker_client",
        "//system/algo_trader/infra/database/redis:redis_services",
        "//system/algo_trader/infra/broker/schwab:schwab_services",
    ],
)
