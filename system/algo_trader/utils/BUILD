load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schema",
    srcs = ["schema.py"],
    deps = [
        requirement("pydantic"),
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//system:__pkg__",  # Available to system package (for project aggregation)
    ],
)
