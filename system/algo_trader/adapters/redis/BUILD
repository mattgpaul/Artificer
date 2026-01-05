load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "redis_adapters",
    srcs = [
        "engine_registry.py",
        "event_bus.py",
        "runtime_config.py",
        "state_store.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//infrastructure/redis",
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
    ],
)
