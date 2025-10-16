load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis_client",
    srcs = ["redis_client.py"],
    deps = [
        "//infrastructure/clients:redis_client",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

py_library(
    name = "schwab_client",
    srcs = ["schwab_client.py"],
    deps = [
        ":redis_client",
        "//infrastructure/clients:schwab_client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

# Unit tests
pytest_test(
    name = "redis_client_test_unit",
    srcs = ["redis_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.clients.redis_client",
    deps = [
        ":redis_client",
    ],
)

pytest_test(
    name = "schwab_client_test_unit",
    srcs = ["schwab_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.clients.schwab_client",
    deps = [
        ":schwab_client",
        ":redis_client",
    ],
)

# Integration tests
pytest_test(
    name = "schwab_client_test_integration",
    srcs = ["schwab_client_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],
    coverage_path = "system.algo_trader.clients.schwab_client",
    deps = [
        ":schwab_client",
        ":redis_client",
    ],
)

