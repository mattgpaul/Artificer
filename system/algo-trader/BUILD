load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schema",
    srcs = ["schema.py"],
    deps = [
        requirement("pydantic"),
    ],
    visibility = [
        "//system/algo-trader:__subpackages__",  # Available to algo-trader subpackages
        "//system:__pkg__",  # Available to system package (for project aggregation)
    ],
)
