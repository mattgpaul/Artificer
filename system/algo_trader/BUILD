# Project aggregation target - collects all algo_trader components (clean slate)
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
        "//system/algo_trader/infra/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
    ],
)
