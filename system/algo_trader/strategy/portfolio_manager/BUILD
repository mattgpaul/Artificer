load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "portfolio_manager_lib",
    srcs = [
        "config_loader.py",
        "portfolio_manager.py",
        "rules/base.py",
        "rules/max_capital_deployed.py",
        "rules/fractional_position_size.py",
    ],
    data = glob(["strategies/*.yaml"]),
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        requirement("pandas"),
        requirement("pyyaml"),
    ],
)

