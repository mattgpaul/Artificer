load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "sec",
    srcs = ["sec.py"],
    visibility = ["//system/algo_trader:__subpackages__"],
    deps = [
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
)
