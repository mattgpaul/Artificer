load("@pip//:requirements.bzl", "requirement")

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

