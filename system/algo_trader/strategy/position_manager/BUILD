load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "position_manager_lib",
    srcs = [
        "position_manager.py",
        "config_loader.py",
    ],
    data = glob(["strategies/*.yaml"]),
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        requirement("pandas"),
        requirement("pyyaml"),
    ],
)

