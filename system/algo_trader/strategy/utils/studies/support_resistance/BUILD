load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "find_peaks",
    srcs = ["find_peaks.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/utils/studies:base_study",
        requirement("pandas"),
        requirement("scipy"),
    ],
)

pytest_test(
    name = "test_find_peaks",
    size = "small",
    coverage_path = "system.algo_trader.strategy.utils.studies.support_resistance.find_peaks",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/utils/studies/support_resistance:test_find_peaks_lib",
)

py_library(
    name = "find_valleys",
    srcs = ["find_valleys.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/utils/studies:base_study",
        requirement("pandas"),
        requirement("scipy"),
    ],
)

pytest_test(
    name = "test_find_valleys",
    size = "small",
    coverage_path = "system.algo_trader.strategy.utils.studies.support_resistance.find_valleys",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/utils/studies/support_resistance:test_find_valleys_lib",
)
