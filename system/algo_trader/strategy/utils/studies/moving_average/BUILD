load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "simple_moving_average",
    srcs = ["simple_moving_average.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/utils/studies:base_study",
        requirement("pandas"),
    ],
)

pytest_test(
    name = "test_simple_moving_average",
    size = "small",
    coverage_path = "system.algo_trader.strategy.utils.studies.moving_average.simple_moving_average",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/utils/studies/moving_average:test_simple_moving_average_lib",
)
