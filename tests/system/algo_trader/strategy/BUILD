load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/strategy:__pkg__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        requirement("pandas"),
        requirement("pytest"),
    ],
)
