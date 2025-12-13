load("@pip//:requirements.bzl", "requirement")

# Engine library - core trading engine abstractions
py_library(
    name = "engine_lib",
    srcs = [
        "core.py",
        "models.py",
        "ports.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/domain/engine:__subpackages__",
    ],
    deps = [
        requirement("pandas"),
        requirement("pydantic"),
        requirement("pandera"),
    ],
)
