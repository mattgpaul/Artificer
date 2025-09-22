load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis_services",
    srcs = [
        "account.py",
        "historical_market.py",
        "live_market.py",
        "watchlist.py",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/clients:redis_client",
        "//system/algo_trader/utils:schema",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)

py_library(
    name = "live_market",
    srcs = ["live_market.py"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/clients:redis_client",
    ],
    visibility = ["//visibility:public"],
)

##### Unit tests #####
pytest_test(
    name = "live_market_test_unit", 
    srcs = ["live_market_test.py",
    "live_market.py"],
    coverage_path = "live_market",
    deps = [
        ":live_market",
    ],
    python_version = "PY3",
    tags = [
        "algo_trader", 
        "unit",
    ],
    args = ["-k", "TestLiveMarketBrokerUnit"],
    size = "small",
    visibility = ["//visibility:public"],
)

# ##### Integration tests #####
# pytest_test(
#     name = "influx_client_test_integration", 
#     srcs = ["influx_client_test.py"],
#     coverage_path = "infrastructure.clients.influx_client",
#     deps = [
#         ":influx_client",
#         requirement("requests"),
#     ],
#     python_version = "PY3",
#     tags = [
#         "infrastructure", 
#         "integration",
#     ],
#     args = ["-k", "TestInfluxDBClientIntegration"],
#     size = "medium",
#     visibility = ["//visibility:public"],
# )