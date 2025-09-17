py_library(
    name = "base_strategy",
    srcs = ["base_strategy.py"],
    deps = [
        "//infrastructure/logging:logger",
    ],
    visibility = [
        "//system/algo-trader:__subpackages__",  # Available to algo-trader subpackages
    ],
)

py_library(
    name = "calculation", 
    srcs = ["calculation.py"],
    deps = [
        # Add any dependencies needed for calculation.py
    ],
    visibility = [
        "//system/algo-trader:__subpackages__",  # Available to algo-trader subpackages
    ],
)
