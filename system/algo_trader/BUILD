load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis_client",
    srcs = ["redis_client.py"],
    deps = [
        "//infrastructure/clients:redis_client",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "schwab_handler",
    srcs = ["schwab_handler.py"],
    deps = [
        ":redis_client",
        "//infrastructure/clients:schwab_client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [
        ":redis_client",
        ":schwab_handler",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//visibility:public"],
)

# Unit tests
pytest_test(
    name = "redis_client_test_unit",
    srcs = ["redis_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.redis_client",
    deps = [
        ":redis_client",
    ],
)

pytest_test(
    name = "schwab_handler_test_unit",
    srcs = ["schwab_handler_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.schwab_handler",
    deps = [
        ":schwab_handler",
        ":redis_client",
    ],
)

# Integration tests
pytest_test(
    name = "schwab_handler_test_integration",
    srcs = ["schwab_handler_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],
    coverage_path = "system.algo_trader.schwab_handler",
    deps = [
        ":schwab_handler",
        ":redis_client",
    ],
)

