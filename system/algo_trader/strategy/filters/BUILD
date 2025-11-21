load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "filters_lib",
    srcs = [
        "base.py",
        "config_loader.py",
        "core.py",
        "filters.py",
        "price_comparison.py",
        "sma_comparison.py",
    ],
    data = glob(["strategies/*.yaml"]),
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies/moving_average:simple_moving_average",
        requirement("pandas"),
        requirement("pyyaml"),
    ],
)
