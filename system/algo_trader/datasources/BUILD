load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "sec",
    srcs = ["sec.py"],
    deps = [
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

