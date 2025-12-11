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
