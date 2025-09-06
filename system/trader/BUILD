load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "market_data_pipeline",
    srcs = [
        "test_data_pipeline.py",
    ],
    deps = [
        "//system/trader/schwab:schwab_services",
        "//system/trader/redis:redis_services",
    ],
    visibility = [
        "//system/trader:__subpackages__",
    ],
)

py_binary(
    name = "test_data_pipeline",
    srcs = [
        "test_data_pipeline.py",
    ],
    deps = [
        ":market_data_pipeline",
    ],
    main = "test_data_pipeline.py",
)