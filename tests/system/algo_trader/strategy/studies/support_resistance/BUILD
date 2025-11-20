load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_find_peaks_lib",
    testonly = True,
    srcs = ["test_find_peaks.py"],
    visibility = ["//system/algo_trader/strategy/studies/support_resistance:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies:base_study",
        "//system/algo_trader/strategy/studies/support_resistance:find_peaks",
        "//tests/system/algo_trader/strategy/studies:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_find_valleys_lib",
    testonly = True,
    srcs = ["test_find_valleys.py"],
    visibility = ["//system/algo_trader/strategy/studies/support_resistance:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies:base_study",
        "//system/algo_trader/strategy/studies/support_resistance:find_valleys",
        "//tests/system/algo_trader/strategy/studies:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)
