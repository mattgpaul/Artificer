load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "moving_average_lib",
    srcs = [
        "ema_crossover.py",
        "sma_crossover.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/strategy:strategy_base",
        "//system/algo_trader/strategy/studies:studies_lib",
        "//system/algo_trader/strategy/studies/moving_average:moving_average_lib",
        requirement("pandas"),
    ],
)


