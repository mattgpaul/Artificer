py_library(
    name = "base_strategy",
    srcs = ["base_strategy.py"],
    deps = [
        "//infrastructure/logging:logger",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
    ],
)

py_library(
    name = "calculation", 
    srcs = ["calculation.py"],
    deps = [
        # Add any dependencies needed for calculation.py
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
    ],
)
