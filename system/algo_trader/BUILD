load("@pip//:requirements.bzl", "requirement")

# Config library for algo_trader system
py_library(
    name = "config",
    srcs = ["config.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader:__subpackages__",
    ],
    deps = [
        "//infrastructure:config",
        requirement("pydantic"),
        requirement("pydantic-settings"),
    ],
)

# Project aggregation target - collects all algo_trader components
py_library(
    name = "library",
    tags = [
        "algo_trader",
        "system",
    ],
    visibility = [
        "//system:__pkg__",  # Available to system package
    ],
    deps = [
        ":config",
        "//system/algo_trader/market_data:market_data_lib",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
        "//system/algo_trader/utils:schema",
    ],
)
