load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "sec",
    srcs = ["sec.py"],
    deps = [
        "//system/algo_trader/clients:influxdb_client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

pytest_test(
    name = "sec_test_unit",
    srcs = ["sec_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.datasources.sec",
    deps = [
        ":sec",
    ],
)

pytest_test(
    name = "sec_test_integration",
    srcs = ["sec_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],
    coverage_path = "system.algo_trader.datasources.sec",
    deps = [
        ":sec",
        "//system/algo_trader/clients:influxdb_client",
    ],
)

