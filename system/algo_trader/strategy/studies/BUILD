load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "studies_lib",
    srcs = ["base_study.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        requirement("pandas"),
    ],
)

pytest_test(
    name = "test_base_study",
    size = "small",
    coverage_path = "system.algo_trader.strategy.studies.base_study",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/studies:test_base_study_lib",
)
